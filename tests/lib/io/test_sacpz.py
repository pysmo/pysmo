"""Tests for pysmo.lib.io._sacpz."""

from pathlib import Path

import pandas as pd
import pytest

from pysmo.lib.io._sacpz import parse_sacpz

SINGLE_FIXTURE = Path(__file__).parent / "sacpz_anmo_single.txt"
BULK_FIXTURE = Path(__file__).parent / "sacpz_anmo_bulk.txt"

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


class TestParseSacpz:
    def test_real_single_record_fixture(self) -> None:
        records = parse_sacpz(SINGLE_FIXTURE.read_text())
        assert len(records) == 1
        record = records[0]
        assert record.network == "IU"
        assert record.station == "ANMO"
        assert record.location == "00"
        assert record.channel == "BHZ"
        assert record.start_date == pd.Timestamp("2014-12-17T18:40:00Z")
        assert record.end_date == pd.Timestamp("2018-07-09T20:45:00Z")
        assert record.input_units == "M"
        assert record.overall_sensitivity == pytest.approx(2.937747e14)
        assert record.reference_sensitivity == pytest.approx(3.404130e9)
        assert len(record.zeros) == 3
        assert len(record.poles) == 5

    def test_real_bulk_fixture_record_count_and_epochs(self) -> None:
        records = parse_sacpz(BULK_FIXTURE.read_text())
        assert len(records) == 9
        for previous, current in zip(records, records[1:]):
            assert previous.end_date == current.start_date
        assert records[-1].end_date is None
        assert {record.channel for record in records} == {"BHZ"}
        assert all(record.reference_sensitivity is not None for record in records)

    def test_minimal_record(self) -> None:
        records = parse_sacpz(MINIMAL_RECORD)
        assert len(records) == 1
        record = records[0]
        assert record.end_date is None
        assert record.overall_sensitivity == pytest.approx(1.0e9)

    def test_minimal_record_has_no_reference_sensitivity(self) -> None:
        """MINIMAL_RECORD has no `* SENSITIVITY` header, unlike real
        EarthScope-produced SAC PZ output; this must not raise, only
        leave reference_sensitivity unset."""
        records = parse_sacpz(MINIMAL_RECORD)
        assert records[0].reference_sensitivity is None

    def test_fortran_d_exponent_tolerated(self) -> None:
        """Hand-written SAC PZ text may use Fortran `D`/`d` exponents instead
        of `E`/`e`, e.g. from older Fortran-heritage tooling."""
        text = (
            MINIMAL_RECORD.replace("e+00", "D+00")
            .replace("e-02", "d-02")
            .replace("1.0e+09", "1.0D+09")
        )
        records = parse_sacpz(text)
        record = records[0]
        assert record.poles == [complex(-1.0e-2, 0.0)]
        assert record.zeros == [complex(0.0, 0.0), complex(0.0, 0.0)]
        assert record.overall_sensitivity == pytest.approx(1.0e9)

    def test_two_concatenated_records(self) -> None:
        text = MINIMAL_RECORD + "\n\n" + MINIMAL_RECORD
        records = parse_sacpz(text)
        assert len(records) == 2

    def test_missing_required_header_raises(self) -> None:
        text = MINIMAL_RECORD.replace("* NETWORK   (KNETWK): IU\n", "")
        with pytest.raises(ValueError, match="missing required header"):
            parse_sacpz(text)

    def test_missing_end_header_line_treated_as_open_epoch(self) -> None:
        # END is not in _REQUIRED_HEADERS, so the header *line* itself may be
        # entirely absent (not just blank); this must not raise a KeyError.
        text = MINIMAL_RECORD.replace("* END               :\n", "")
        records = parse_sacpz(text)
        assert len(records) == 1
        assert records[0].end_date is None

    def test_missing_zeros_block_raises(self) -> None:
        text = MINIMAL_RECORD.replace("ZEROS\t2\n", "")
        with pytest.raises(ValueError, match="Expected 'ZEROS' block"):
            parse_sacpz(text)

    def test_missing_poles_block_raises(self) -> None:
        lines = MINIMAL_RECORD.splitlines()
        poles_index = next(
            i for i, line in enumerate(lines) if line.startswith("POLES")
        )
        text = "\n".join(lines[:poles_index] + lines[poles_index + 2 :]) + "\n"
        with pytest.raises(ValueError, match="Expected 'POLES' block"):
            parse_sacpz(text)

    def test_missing_constant_raises(self) -> None:
        lines = MINIMAL_RECORD.splitlines()
        constant_index = next(
            i for i, line in enumerate(lines) if line.startswith("CONSTANT")
        )
        text = "\n".join(lines[:constant_index]) + "\n"
        with pytest.raises(ValueError, match="Expected 'CONSTANT'"):
            parse_sacpz(text)

    def test_non_comment_line_where_header_expected_raises(self) -> None:
        text = "not a comment header\n" + MINIMAL_RECORD
        with pytest.raises(ValueError, match="Expected a comment header line"):
            parse_sacpz(text)

    def test_truncated_zeros_block_raises(self) -> None:
        lines = MINIMAL_RECORD.splitlines()
        zeros_index = next(
            i for i, line in enumerate(lines) if line.startswith("ZEROS")
        )
        # Claim 3 zeros but only provide the 2 that follow, then end the text.
        text = "\n".join(
            [
                *lines[:zeros_index],
                "ZEROS\t3",
                *lines[zeros_index + 1 : zeros_index + 3],
            ]
        )
        with pytest.raises(ValueError, match="Unexpected end of text"):
            parse_sacpz(text)
