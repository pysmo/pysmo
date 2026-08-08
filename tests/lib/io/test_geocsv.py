"""Tests for pysmo.lib.io._geocsv."""

from pathlib import Path

import numpy as np
import numpy.testing as npt
import pandas as pd
import pytest

from pysmo import MiniSeismogram
from pysmo.classes import GeoCsvSeismogram
from pysmo.lib.io._geocsv import (
    GeoCsvDataset,
    _TimeseriesSegment,
    extract_geocsv_timeseries,
    merge_geocsv_timeseries,
    parse_geocsv,
    write_geocsv,
)

FIXTURE = Path(__file__).parent / "assets" / "dataselect_response.geocsv"

SIMPLE = """\
# dataset: GeoCSV 2.0
# delimiter: ,
# field_unit: UTC, Counts
# field_type: datetime, INTEGER
# SID: IU_ANMO_00_LHZ
# sample_count: 3
# sample_rate_hz: 1.0
# start_time: 2010-02-27T06:30:00Z
Time, Sample
2010-02-27T06:30:00Z, 1
2010-02-27T06:30:01Z, 2
2010-02-27T06:30:02Z, 3
"""


def make_segment(
    start_time: str = "2010-02-27T06:30:00Z",
    sample_rate_hz: float = 1.0,
    sample_count: int = 3,
    sid: str = "IU_ANMO_00_LHZ",
    data: list[float] | None = None,
) -> _TimeseriesSegment:
    if data is None:
        data = [1.0] * sample_count
    return _TimeseriesSegment(
        start_time=pd.Timestamp(start_time),
        sample_rate_hz=sample_rate_hz,
        sample_count=sample_count,
        sid=sid,
        data=np.array(data),
    )


class TestParseGeoCsv:
    def test_simple(self) -> None:
        datasets = parse_geocsv(SIMPLE)
        assert len(datasets) == 1
        dataset = datasets[0]
        assert dataset.headers["dataset"] == "GeoCSV 2.0"
        assert dataset.headers["sid"] == "IU_ANMO_00_LHZ"
        assert dataset.column_names == ["Time", "Sample"]
        assert dataset.rows == [
            ["2010-02-27T06:30:00Z", "1"],
            ["2010-02-27T06:30:01Z", "2"],
            ["2010-02-27T06:30:02Z", "3"],
        ]

    def test_keyword_whitespace_variants(self) -> None:
        text = "#dataset:GeoCSV 2.0\n#  sample_count  :  2  \nTime,Sample\na,1\nb,2\n"
        datasets = parse_geocsv(text)
        assert len(datasets) == 1
        assert datasets[0].headers["dataset"] == "GeoCSV 2.0"
        assert datasets[0].headers["sample_count"] == "2"

    def test_plain_comment_ignored(self) -> None:
        text = "# dataset: GeoCSV 2.0\n# a comment without keyword\nTime,Sample\na,1\n"
        datasets = parse_geocsv(text)
        assert len(datasets) == 1
        assert datasets[0].rows == [["a", "1"]]

    def test_delimiter_pipe(self) -> None:
        text = (
            "# dataset: GeoCSV 2.0\n"
            "# delimiter: |\n"
            "Network|Station|Latitude\n"
            "IU|ANMO|34.9459\n"
        )
        dataset = parse_geocsv(text)[0]
        assert dataset.column_names == ["Network", "Station", "Latitude"]
        assert dataset.rows == [["IU", "ANMO", "34.9459"]]

    def test_delimiter_escaped_space(self) -> None:
        text = "# dataset: GeoCSV 2.0\n# delimiter: \\s\nTime Sample\na 1\n"
        dataset = parse_geocsv(text)[0]
        assert dataset.column_names == ["Time", "Sample"]
        assert dataset.rows == [["a", "1"]]

    def test_quoted_field_with_delimiter(self) -> None:
        text = '# dataset: GeoCSV 2.0\n# delimiter: ,\nStation, Sample\n"ANMO, IU", 1\n'
        dataset = parse_geocsv(text)[0]
        assert dataset.rows == [["ANMO, IU", "1"]]

    def test_preserves_empty_edge_fields(self) -> None:
        text = "# dataset: GeoCSV 2.0\n# delimiter: ,\nA,B,C\n,1,\n"
        dataset = parse_geocsv(text)[0]
        assert dataset.rows == [["", "1", ""]]

    def test_multi_dataset(self) -> None:
        datasets = parse_geocsv(SIMPLE + SIMPLE)
        assert len(datasets) == 2
        assert datasets[0].rows == datasets[1].rows

    def test_header_line_any_name(self) -> None:
        text = "# dataset: GeoCSV 2.0\nEpoch, Value\n1, 2\n"
        dataset = parse_geocsv(text)[0]
        assert dataset.column_names == ["Epoch", "Value"]
        assert dataset.rows == [["1", "2"]]

    def test_no_leading_dataset_keyword(self) -> None:
        text = "# sample_count: 1\nTime,Sample\na,1\n"
        datasets = parse_geocsv(text)
        assert len(datasets) == 1
        assert datasets[0].headers["sample_count"] == "1"

    def test_empty_text(self) -> None:
        assert parse_geocsv("") == []


class TestExtractGeocsvTimeseries:
    def test_simple(self) -> None:
        segment = extract_geocsv_timeseries(parse_geocsv(SIMPLE)[0])
        assert segment.start_time == pd.Timestamp("2010-02-27T06:30:00Z")
        assert segment.sample_rate_hz == 1.0
        assert segment.sample_count == 3
        assert segment.sid == "IU_ANMO_00_LHZ"
        npt.assert_allclose(segment.data, [1.0, 2.0, 3.0])
        assert segment.data.dtype == np.float64

    def test_field_type_column_detection(self) -> None:
        text = (
            "# dataset: GeoCSV 2.0\n"
            "# field_type: float, datetime\n"
            "# sample_count: 1\n"
            "# sample_rate_hz: 1.0\n"
            "# start_time: 2010-02-27T06:30:00Z\n"
            "Sample, Time\n"
            "42, 2010-02-27T06:30:00Z\n"
        )
        segment = extract_geocsv_timeseries(parse_geocsv(text)[0])
        npt.assert_allclose(segment.data, [42.0])

    def test_field_type_column_out_of_range(self) -> None:
        """field_type declares more columns than a data row actually has."""
        text = (
            "# dataset: GeoCSV 2.0\n"
            "# field_type: datetime, integer\n"
            "# sample_count: 1\n"
            "# sample_rate_hz: 1.0\n"
            "# start_time: 2010-02-27T06:30:00Z\n"
            "Sample\n"
            "42\n"
        )
        with pytest.raises(ValueError, match="fewer than 2 fields"):
            extract_geocsv_timeseries(parse_geocsv(text)[0])

    def test_missing_field_type(self) -> None:
        text = (
            "# dataset: GeoCSV 2.0\n"
            "# sample_count: 1\n"
            "# sample_rate_hz: 1.0\n"
            "# start_time: 2010-02-27T06:30:00Z\n"
            "Time, Sample\n"
            "2010-02-27T06:30:00Z, 42\n"
        )
        with pytest.raises(ValueError, match="Cannot determine sample column"):
            extract_geocsv_timeseries(parse_geocsv(text)[0])

    def test_missing_header(self) -> None:
        text = "# dataset: GeoCSV 2.0\n# sample_count: 0\nTime,Sample\n"
        with pytest.raises(ValueError, match="missing required timeseries header"):
            extract_geocsv_timeseries(parse_geocsv(text)[0])

    def test_sample_count_mismatch(self) -> None:
        truncated = SIMPLE.replace("# sample_count: 3", "# sample_count: 5")
        with pytest.raises(ValueError, match="declares sample_count 5"):
            extract_geocsv_timeseries(parse_geocsv(truncated)[0])

    def test_missing_sid(self) -> None:
        text = (
            "# dataset: GeoCSV 2.0\n"
            "# sample_count: 0\n"
            "# sample_rate_hz: 1.0\n"
            "# start_time: 2010-02-27T06:30:00Z\n"
            "Time, Sample\n"
        )
        assert extract_geocsv_timeseries(parse_geocsv(text)[0]).sid == ""


class TestMergeGeocsvTimeseries:
    def test_single_segment(self) -> None:
        segment = make_segment()
        assert merge_geocsv_timeseries([segment]) is segment

    def test_merge_contiguous(self) -> None:
        first = make_segment(data=[1.0, 2.0, 3.0])
        second = make_segment(start_time="2010-02-27T06:30:03Z", data=[4.0, 5.0, 6.0])
        merged = merge_geocsv_timeseries([first, second])
        assert merged.start_time == first.start_time
        assert merged.sample_count == 6
        npt.assert_allclose(merged.data, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])

    def test_zero_sample_segment_skipped(self) -> None:
        first = make_segment(data=[1.0, 2.0, 3.0])
        empty = make_segment(start_time="2010-02-27T06:35:00Z", sample_count=0, data=[])
        second = make_segment(start_time="2010-02-27T06:30:03Z", data=[4.0, 5.0, 6.0])
        merged = merge_geocsv_timeseries([first, empty, second])
        assert merged.sample_count == 6

    def test_all_segments_empty(self) -> None:
        empty = make_segment(sample_count=0, data=[])
        with pytest.raises(ValueError, match="No non-empty timeseries segments"):
            merge_geocsv_timeseries([empty])

    def test_sid_mismatch(self) -> None:
        first = make_segment()
        second = make_segment(start_time="2010-02-27T06:30:03Z", sid="IU_ANMO_00_LH1")
        with pytest.raises(ValueError, match="different channels"):
            merge_geocsv_timeseries([first, second])

    def test_sample_rate_mismatch(self) -> None:
        first = make_segment()
        second = make_segment(start_time="2010-02-27T06:30:03Z", sample_rate_hz=2.0)
        with pytest.raises(ValueError, match="different sample rates"):
            merge_geocsv_timeseries([first, second])

    def test_sample_rate_jitter_still_raises(self) -> None:
        """Even a tiny sample-rate difference is rejected; picking a
        canonical rate between near-equal floats is not this function's
        call to make."""
        first = make_segment(data=[1.0, 2.0, 3.0])
        second = make_segment(
            start_time="2010-02-27T06:30:03Z",
            sample_rate_hz=1.0 + 1e-8,
            data=[4.0, 5.0, 6.0],
        )
        with pytest.raises(ValueError, match="different sample rates"):
            merge_geocsv_timeseries([first, second])

    def test_sample_rate_jitter_merges_with_auto_delta(self) -> None:
        first = make_segment(data=[1.0, 2.0, 3.0])
        second = make_segment(
            start_time="2010-02-27T06:30:03Z",
            sample_rate_hz=1.0 + 1e-8,
            data=[4.0, 5.0, 6.0],
        )
        merged = merge_geocsv_timeseries([first, second], auto_delta=True)
        assert merged.sample_count == 6
        npt.assert_allclose(merged.sample_rate_hz, 1.0 + 1e-8)
        npt.assert_allclose(merged.data, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])

    def test_data_gap(self) -> None:
        first = make_segment()
        second = make_segment(start_time="2010-02-27T06:30:10Z")
        with pytest.raises(ValueError, match="Data gap of 7.000000 s"):
            merge_geocsv_timeseries([first, second])

    def test_small_gap_raises(self) -> None:
        first = make_segment()
        second = make_segment(start_time="2010-02-27T06:30:03.6Z")
        with pytest.raises(ValueError, match="Data gap of 0.600000 s"):
            merge_geocsv_timeseries([first, second])

    def test_boundary_timestamp_jitter_within_tolerance(self) -> None:
        first = make_segment()
        second = make_segment(start_time="2010-02-27T06:30:03.0000005Z")
        merged = merge_geocsv_timeseries([first, second])
        assert merged.sample_count == 6

    def test_out_of_order_input(self) -> None:
        first = make_segment(data=[1.0, 2.0, 3.0])
        second = make_segment(start_time="2010-02-27T06:30:03Z", data=[4.0, 5.0, 6.0])
        merged = merge_geocsv_timeseries([second, first])
        assert merged.start_time == first.start_time
        npt.assert_allclose(merged.data, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])

    def test_negative_gap_tolerance_factor_raises(self) -> None:
        segment = make_segment()
        with pytest.raises(
            ValueError, match="gap_tolerance_factor must be non-negative"
        ):
            merge_geocsv_timeseries([segment], gap_tolerance_factor=-1)


def test_real_dataselect_response() -> None:
    """Parse a captured response from the EarthScope dataselect service."""
    datasets = parse_geocsv(FIXTURE.read_text())
    assert len(datasets) == 1
    dataset = datasets[0]
    assert dataset.delimiter == ","
    assert dataset.headers["latitude_deg"] == "34.945981"
    segment = extract_geocsv_timeseries(dataset)
    assert segment.sid == "IU_ANMO_00_LHZ"
    assert segment.sample_rate_hz == 1.0
    assert segment.sample_count == 60
    assert segment.start_time == pd.Timestamp("2010-02-27T06:30:00.069538Z")
    assert segment.data[0] == -47297.0
    assert segment.data[-1] == -49476.0


def test_dataset_delimiter_default() -> None:
    assert GeoCsvDataset().delimiter == ","


class TestWriteGeocsv:
    def make_seismogram(
        self,
        data: list[float] | None = None,
        sid: str = "IU_ANMO_00_LHZ",
    ) -> GeoCsvSeismogram:
        return GeoCsvSeismogram(
            begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
            delta=pd.Timedelta(seconds=1.0),
            data=np.array(data if data is not None else [1.0, 2.0, 3.0]),
            sid=sid,
        )

    def test_round_trip(self, tmp_path: Path) -> None:
        seismogram = self.make_seismogram()
        path = tmp_path / "out.geocsv"
        write_geocsv(seismogram, path)
        segment = extract_geocsv_timeseries(parse_geocsv(path.read_text())[0])
        assert segment.start_time == seismogram.begin_time
        assert segment.sample_rate_hz == pytest.approx(1.0)
        npt.assert_allclose(segment.data, seismogram.data)

    def test_sid_written_when_present(self, tmp_path: Path) -> None:
        seismogram = self.make_seismogram()
        path = tmp_path / "out.geocsv"
        write_geocsv(seismogram, path)
        assert "# SID: IU_ANMO_00_LHZ" in path.read_text()

    def test_sid_omitted_when_absent(self, tmp_path: Path) -> None:
        """A bare MiniSeismogram has no `sid` attribute at all — write_geocsv
        must not raise, and must simply omit the `# SID:` header line."""
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
            delta=pd.Timedelta(seconds=1.0),
            data=np.array([1.0, 2.0, 3.0]),
        )
        assert not hasattr(seismogram, "sid")
        path = tmp_path / "out.geocsv"
        write_geocsv(seismogram, path)
        assert "SID" not in path.read_text()
        segment = extract_geocsv_timeseries(parse_geocsv(path.read_text())[0])
        assert segment.sid == ""

    def test_integral_data_written_as_integer_field_type(self, tmp_path: Path) -> None:
        seismogram = self.make_seismogram(data=[1.0, 2.0, 3.0])
        path = tmp_path / "out.geocsv"
        write_geocsv(seismogram, path)
        assert "field_type: datetime, integer" in path.read_text()

    def test_non_integral_data_round_trips_without_truncation(
        self, tmp_path: Path
    ) -> None:
        """A hardcoded `int(sample)` would silently truncate 1.5 to 1 —
        regression guard for that fix."""
        seismogram = self.make_seismogram(data=[1.5, 2.25, 3.0])
        path = tmp_path / "out.geocsv"
        write_geocsv(seismogram, path)
        text = path.read_text()
        assert "field_type: datetime, float" in text
        segment = extract_geocsv_timeseries(parse_geocsv(text)[0])
        npt.assert_allclose(segment.data, [1.5, 2.25, 3.0])

    def test_infinite_value_does_not_raise(self, tmp_path: Path) -> None:
        """`inf == round(inf)` is True, so a naive integral check would
        route `inf` into `int(inf)`, which raises OverflowError — regression
        guard for the np.isfinite(...) fix."""
        seismogram = self.make_seismogram(data=[1.0, 2.0, np.inf])
        path = tmp_path / "out.geocsv"
        write_geocsv(seismogram, path)
        text = path.read_text()
        assert "field_type: datetime, float" in text
        segment = extract_geocsv_timeseries(parse_geocsv(text)[0])
        npt.assert_allclose(segment.data, [1.0, 2.0, np.inf])

    def test_multi_record(self, tmp_path: Path) -> None:
        seg1 = self.make_seismogram(sid="IU_ANMO_00_LHZ")
        seg2 = self.make_seismogram(data=[4.0, 5.0, 6.0], sid="IU_ANMO_00_BHZ")
        path = tmp_path / "multi.geocsv"
        write_geocsv([seg1, seg2], path)
        datasets = parse_geocsv(path.read_text())
        assert len(datasets) == 2
        assert datasets[0].headers["sid"] == "IU_ANMO_00_LHZ"
        assert datasets[1].headers["sid"] == "IU_ANMO_00_BHZ"

    def test_empty_sequence_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="empty sequence"):
            write_geocsv([], tmp_path / "out.geocsv")
