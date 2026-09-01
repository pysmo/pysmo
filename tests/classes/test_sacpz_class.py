"""Tests for pysmo.classes.SacPZ."""

from pathlib import Path

import pandas as pd
import pytest

from pysmo import MiniStation
from pysmo.classes import SacPZ

SINGLE_FIXTURE = (
    Path(__file__).parent.parent / "lib" / "io" / "assets" / "sacpz_anmo_single.txt"
)
BULK_FIXTURE = (
    Path(__file__).parent.parent / "lib" / "io" / "assets" / "sacpz_anmo_bulk.txt"
)

MINIMAL_RECORD = """\
* NETWORK   (KNETWK): IU
* STATION    (KSTNM): ANMO
* LOCATION   (KHOLE): 00
* CHANNEL   (KCMPNM): BHZ
* START             : 2018-07-09T20:45:00
* END               :
* INPUT UNIT        : M
ZEROS\t2
\t+0.000000e+00\t+0.000000e+00
\t+0.000000e+00\t+0.000000e+00
POLES\t1
\t-1.000000e-02\t+0.000000e+00
CONSTANT\t1.0e+09
"""


class TestFromText:
    def test_real_single_record_fixture(self) -> None:
        response = SacPZ.from_text(SINGLE_FIXTURE.read_text())
        assert response.network == "IU"
        assert response.station == "ANMO"
        assert response.location == "00"
        assert response.channel == "BHZ"
        assert response.start_date == pd.Timestamp("2014-12-17T18:40:00Z")
        assert response.end_date == pd.Timestamp("2018-07-09T20:45:00Z")
        assert response.input_units == "M"
        assert response.overall_sensitivity == pytest.approx(2.937747e14)
        assert response.reference_sensitivity == pytest.approx(3.404130e9)

    def test_minimal_record(self) -> None:
        response = SacPZ.from_text(MINIMAL_RECORD)
        assert response.end_date is None
        assert len(response.poles) == 1
        assert len(response.zeros) == 2
        assert response.reference_sensitivity is None

    def test_zero_records_raises(self) -> None:
        with pytest.raises(ValueError, match="found 0"):
            SacPZ.from_text("")

    def test_multiple_records_raises(self) -> None:
        text = MINIMAL_RECORD + "\n\n" + MINIMAL_RECORD
        with pytest.raises(ValueError, match="found 2"):
            SacPZ.from_text(text)


class TestAllFromText:
    def test_real_bulk_fixture(self) -> None:
        responses = SacPZ.all_from_text(BULK_FIXTURE.read_text())
        assert len(responses) == 9
        for response in responses:
            assert response.network == "IU"
            assert response.station == "ANMO"
        for previous, current in zip(responses, responses[1:]):
            assert previous.end_date == current.start_date
        assert responses[-1].end_date is None

    def test_single_record_still_returns_a_list(self) -> None:
        responses = SacPZ.all_from_text(MINIMAL_RECORD)
        assert len(responses) == 1


class TestFetch:
    @pytest.fixture()
    def station(self) -> MiniStation:
        return MiniStation(
            name="ANMO",
            network="IU",
            location="00",
            channel="BHZ",
            latitude=34.945981,
            longitude=-106.457133,
        )

    def test_fetches_and_parses(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        calls: list[tuple[str, dict[str, object]]] = []

        def fake_http_get(
            url: str, fields: dict[str, object], **kwargs: object
        ) -> bytes:
            calls.append((url, fields))
            return SINGLE_FIXTURE.read_bytes()

        monkeypatch.setattr("pysmo.tools.web.http_get", fake_http_get)

        response = SacPZ.fetch(station=station)

        assert response.network == "IU"
        assert response.station == "ANMO"

        _, fields = calls[0]
        assert fields["net"] == "IU"
        assert fields["sta"] == "ANMO"
        assert fields["loc"] == "00"
        assert fields["cha"] == "BHZ"
        assert "time" not in fields

    def test_time_param_passed_through_when_given(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        calls: list[tuple[str, dict[str, object]]] = []

        def fake_http_get(
            url: str, fields: dict[str, object], **kwargs: object
        ) -> bytes:
            calls.append((url, fields))
            return SINGLE_FIXTURE.read_bytes()

        monkeypatch.setattr("pysmo.tools.web.http_get", fake_http_get)

        SacPZ.fetch(station=station, time=pd.Timestamp("2016-01-01T00:00:00Z"))

        _, fields = calls[0]
        assert fields["time"] == "2016-01-01T00:00:00+00:00"
