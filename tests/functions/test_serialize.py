"""Tests for pysmo.functions._serialize."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pysmo import MiniSeismogram
from pysmo.classes import GeoCsvSeismogram
from pysmo.functions import (
    clone_to_mini,
    seismogram_checksum,
    seismogram_from_json,
    seismogram_to_json,
)
from pysmo.functions._serialize import _is_serializable_seismogram
from pysmo.tools.iccs import MiniIccsSeismogram

_T0 = pd.Timestamp("2010-02-27T06:44:00Z")


def _to_iccs(source: MiniSeismogram, **extra: object) -> MiniIccsSeismogram:
    return clone_to_mini(MiniIccsSeismogram, source, update={"t0": _T0, **extra})


@pytest.fixture()
def seismogram() -> MiniSeismogram:
    return MiniSeismogram(
        begin_time=pd.Timestamp("2010-02-27T06:40:00Z"),
        delta=pd.Timedelta(seconds=1),
        data=np.array([1.0, 2.0, 3.0, 4.0]),
    )


class TestChecksum:
    def test_is_stable_and_prefixed(self, seismogram: MiniSeismogram) -> None:
        digest = seismogram_checksum(seismogram)
        assert digest.startswith("sha256:")
        assert seismogram_checksum(seismogram) == digest

    def test_covers_only_the_protocol_members(self, seismogram: MiniSeismogram) -> None:
        richer = _to_iccs(seismogram, flip=True)
        assert seismogram_checksum(richer) == seismogram_checksum(seismogram)

    @pytest.mark.parametrize(
        "update",
        [
            {"data": np.array([1.0, 2.0, 3.0, 5.0])},
            {"data": np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)},
            {"begin_time": pd.Timestamp("2010-02-27T06:41:00Z")},
            {"delta": pd.Timedelta(seconds=2)},
        ],
    )
    def test_sensitive_to_each_component(
        self, seismogram: MiniSeismogram, update: dict[str, object]
    ) -> None:
        changed = clone_to_mini(MiniSeismogram, seismogram, update=update)
        assert seismogram_checksum(changed) != seismogram_checksum(seismogram)

    def test_sensitive_to_shape_at_equal_bytes(self) -> None:
        flat = MiniSeismogram(
            begin_time=pd.Timestamp("2010-02-27T06:40:00Z"),
            delta=pd.Timedelta(seconds=1),
            data=np.arange(4.0),
        )
        reshaped = MiniSeismogram(
            begin_time=flat.begin_time,
            delta=flat.delta,
            data=np.arange(4.0).reshape(2, 2),
        )
        assert seismogram_checksum(flat) != seismogram_checksum(reshaped)


class TestGate:
    def test_accepts_a_value_object(self, seismogram: MiniSeismogram) -> None:
        assert _is_serializable_seismogram(seismogram) is True

    def test_rejects_a_non_attrs_object(self) -> None:
        assert _is_serializable_seismogram(object()) is False

    def test_rejects_a_sac_seismogram_live_view(
        self, reference_event_assets: dict[str, Path]
    ) -> None:
        from pysmo.classes import SAC

        sac_seismogram = SAC.from_file(reference_event_assets["sac_bhz"]).seismogram
        assert _is_serializable_seismogram(sac_seismogram) is False


class TestRoundTrip:
    @pytest.mark.parametrize(
        "transform",
        [
            lambda s: clone_to_mini(MiniSeismogram, s),
            lambda s: _to_iccs(s, flip=True),
            lambda s: GeoCsvSeismogram(
                begin_time=s.begin_time,
                delta=s.delta,
                data=s.data,
                sourceid="IU_ANMO_00_BHZ",
            ),
        ],
        ids=["mini", "iccs", "geocsv"],
    )
    def test_every_value_object_round_trips(
        self, seismogram: MiniSeismogram, transform: object
    ) -> None:
        original = transform(seismogram)  # type: ignore[operator]
        restored = seismogram_from_json(seismogram_to_json(original))

        assert type(restored) is type(original)
        assert restored == original
        assert np.array_equal(restored.data, seismogram.data)

    def test_nan_samples_round_trip_and_pass_verify(self) -> None:
        gappy = MiniSeismogram(
            begin_time=pd.Timestamp("2010-02-27T06:40:00Z"),
            delta=pd.Timedelta(seconds=1),
            data=np.array([1.0, np.nan, 3.0, np.nan]),
        )
        blob = seismogram_to_json(gappy, verify=True)  # no false "lossy" raise
        restored = seismogram_from_json(blob)
        assert np.array_equal(restored.data, gappy.data, equal_nan=True)

    def test_decoded_data_is_writable(self, seismogram: MiniSeismogram) -> None:
        restored = seismogram_from_json(seismogram_to_json(seismogram))
        restored.data[0] = 99.0  # would raise if the buffer were read-only

    def test_explicit_cls_skips_the_embedded_name(
        self, seismogram: MiniSeismogram
    ) -> None:
        blob = seismogram_to_json(seismogram)
        assert seismogram_from_json(blob, cls=MiniSeismogram) == seismogram


class TestEncodeErrors:
    def test_non_serialisable_seismogram_raises(
        self, reference_event_assets: dict[str, Path]
    ) -> None:
        from pysmo.classes import SAC

        sac_seismogram = SAC.from_file(reference_event_assets["sac_bhz"]).seismogram
        with pytest.raises(TypeError, match="clone_to_mini"):
            seismogram_to_json(sac_seismogram)

    def test_unhookable_field_raises(self, seismogram: MiniSeismogram) -> None:
        result = _to_iccs(seismogram)
        result.extra["thing"] = np.array([1.0, 2.0])
        with pytest.raises(TypeError, match="clone_to_mini"):
            seismogram_to_json(result)

    def test_verify_catches_a_lossy_hook(self, seismogram: MiniSeismogram) -> None:
        result = _to_iccs(seismogram)
        # A tuple survives JSON only as a list, so verify sees a changed value.
        result.extra["thing"] = (1, 2, 3)
        with pytest.raises(TypeError, match="round trip"):
            seismogram_to_json(result, verify=True)

    def test_verify_is_off_by_default(self, seismogram: MiniSeismogram) -> None:
        result = _to_iccs(seismogram)
        result.extra["thing"] = (1, 2, 3)
        seismogram_to_json(result)  # no verify, no raise


class TestDecodeErrors:
    def test_rejects_a_non_attrs_target(self) -> None:
        blob = json.dumps({"cls": "pysmo:Seismogram", "v": 1, "payload": {}}).encode()
        with pytest.raises(TypeError, match="not an attrs class"):
            seismogram_from_json(blob, cls=dict)  # type: ignore[type-var]
        with pytest.raises(TypeError, match="not an attrs class"):
            seismogram_from_json(blob)

    @pytest.mark.parametrize(
        "blob",
        [
            b"not json at all",
            json.dumps([1, 2, 3]).encode(),
            json.dumps({"cls": "pysmo:MiniSeismogram", "payload": {}}).encode(),
        ],
    )
    def test_rejects_a_malformed_document(self, blob: bytes) -> None:
        with pytest.raises(TypeError):
            seismogram_from_json(blob)

    def test_rejects_an_unsupported_version(self, seismogram: MiniSeismogram) -> None:
        tampered = json.loads(seismogram_to_json(seismogram))
        tampered["v"] = 99
        with pytest.raises(TypeError, match="version 99"):
            seismogram_from_json(json.dumps(tampered).encode())

    def test_rejects_a_non_integer_version(self, seismogram: MiniSeismogram) -> None:
        tampered = json.loads(seismogram_to_json(seismogram))
        tampered["v"] = [1]
        with pytest.raises(TypeError, match="version"):
            seismogram_from_json(json.dumps(tampered).encode())

    @pytest.mark.parametrize("module", ["subprocess", "this_module_is_not_pysmo"])
    def test_refuses_to_import_an_untrusted_module(self, module: str) -> None:
        import sys

        already_loaded = module in sys.modules
        blob = json.dumps({"cls": f"{module}:Thing", "v": 1, "payload": {}}).encode()
        with pytest.raises(TypeError, match="not in the trusted set"):
            seismogram_from_json(blob)
        if not already_loaded:
            assert module not in sys.modules

    def test_trusted_modules_can_be_widened(self, seismogram: MiniSeismogram) -> None:
        blob = seismogram_to_json(seismogram)
        assert seismogram_from_json(blob, trusted_modules=("pysmo", "other")) == (
            seismogram
        )

    def test_rejects_a_hostile_ndarray_dtype(self, seismogram: MiniSeismogram) -> None:
        tampered = json.loads(seismogram_to_json(seismogram))
        tampered["payload"]["data"]["dtype"] = "object"
        with pytest.raises(TypeError, match="does not fit"):
            seismogram_from_json(json.dumps(tampered).encode())

    def test_reports_a_moved_class_cleanly(self) -> None:
        blob = json.dumps(
            {"cls": "pysmo.gone:Vanished", "v": 1, "payload": {}}
        ).encode()
        with pytest.raises(TypeError, match="can no longer be imported"):
            seismogram_from_json(blob)

    def test_explicit_cls_survives_a_moved_class(
        self, seismogram: MiniSeismogram
    ) -> None:
        blob = seismogram_to_json(seismogram)
        tampered = json.loads(blob)
        tampered["cls"] = "pysmo.gone:Vanished"
        restored = seismogram_from_json(
            json.dumps(tampered).encode(), cls=MiniSeismogram
        )
        assert restored == seismogram
