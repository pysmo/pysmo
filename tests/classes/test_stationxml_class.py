"""Tests for pysmo.classes.StationXMLResponse."""

from pathlib import Path

import pandas as pd
import pytest

from pysmo import MiniStation, Response, StagedResponse
from pysmo.classes import StationXMLResponse

SINGLE_EPOCH_FIXTURE = (
    Path(__file__).parent.parent
    / "lib"
    / "io"
    / "assets"
    / "stationxml_anmo_single.xml"
)
BULK_FIXTURE = (
    Path(__file__).parent.parent / "lib" / "io" / "assets" / "stationxml_anmo_bulk.xml"
)

OVERLAPPING_EPOCHS = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00" startDate="2000-01-01T00:00:00.0000"
                endDate="2020-01-01T00:00:00.0000">
        <Response>
          <InstrumentSensitivity>
            <Value>1.0E9</Value>
            <InputUnits><Name>m/s</Name></InputUnits>
          </InstrumentSensitivity>
          <Stage number="1">
            <PolesZeros>
              <PzTransferFunctionType>LAPLACE (RADIANS/SECOND)</PzTransferFunctionType>
              <NormalizationFactor>1.0</NormalizationFactor>
              <Zero number="0"><Real>0.0</Real><Imaginary>0.0</Imaginary></Zero>
              <Pole number="0"><Real>-1.0</Real><Imaginary>0.0</Imaginary></Pole>
            </PolesZeros>
            <Decimation><InputSampleRate>40.0</InputSampleRate><Factor>1</Factor></Decimation>
            <StageGain><Value>1.0</Value><Frequency>1.0</Frequency></StageGain>
          </Stage>
        </Response>
      </Channel>
      <Channel code="BHZ" locationCode="00" startDate="2005-01-01T00:00:00.0000"
                endDate="2025-01-01T00:00:00.0000">
        <Response>
          <InstrumentSensitivity>
            <Value>2.0E9</Value>
            <InputUnits><Name>m/s</Name></InputUnits>
          </InstrumentSensitivity>
          <Stage number="1">
            <PolesZeros>
              <PzTransferFunctionType>LAPLACE (RADIANS/SECOND)</PzTransferFunctionType>
              <NormalizationFactor>1.0</NormalizationFactor>
              <Zero number="0"><Real>0.0</Real><Imaginary>0.0</Imaginary></Zero>
              <Pole number="0"><Real>-2.0</Real><Imaginary>0.0</Imaginary></Pole>
            </PolesZeros>
            <Decimation><InputSampleRate>40.0</InputSampleRate><Factor>1</Factor></Decimation>
            <StageGain><Value>1.0</Value><Frequency>1.0</Frequency></StageGain>
          </Stage>
        </Response>
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""

MULTIPLE_LOCATIONS_AND_CHANNELS = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00" startDate="2000-01-01T00:00:00.0000">
        <Response>
          <InstrumentSensitivity>
            <Value>1.0E9</Value>
            <InputUnits><Name>m/s</Name></InputUnits>
          </InstrumentSensitivity>
          <Stage number="1">
            <PolesZeros>
              <PzTransferFunctionType>LAPLACE (RADIANS/SECOND)</PzTransferFunctionType>
              <NormalizationFactor>1.0</NormalizationFactor>
              <Zero number="0"><Real>0.0</Real><Imaginary>0.0</Imaginary></Zero>
              <Pole number="0"><Real>-1.0</Real><Imaginary>0.0</Imaginary></Pole>
            </PolesZeros>
            <Decimation><InputSampleRate>40.0</InputSampleRate><Factor>1</Factor></Decimation>
            <StageGain><Value>1.0</Value><Frequency>1.0</Frequency></StageGain>
          </Stage>
        </Response>
      </Channel>
      <Channel code="BHN" locationCode="00" startDate="2000-01-01T00:00:00.0000">
        <Response>
          <InstrumentSensitivity>
            <Value>2.0E9</Value>
            <InputUnits><Name>m/s</Name></InputUnits>
          </InstrumentSensitivity>
          <Stage number="1">
            <PolesZeros>
              <PzTransferFunctionType>LAPLACE (RADIANS/SECOND)</PzTransferFunctionType>
              <NormalizationFactor>1.0</NormalizationFactor>
              <Zero number="0"><Real>0.0</Real><Imaginary>0.0</Imaginary></Zero>
              <Pole number="0"><Real>-2.0</Real><Imaginary>0.0</Imaginary></Pole>
            </PolesZeros>
            <Decimation><InputSampleRate>40.0</InputSampleRate><Factor>1</Factor></Decimation>
            <StageGain><Value>1.0</Value><Frequency>1.0</Frequency></StageGain>
          </Stage>
        </Response>
      </Channel>
      <Channel code="BHZ" locationCode="10" startDate="2000-01-01T00:00:00.0000">
        <Response>
          <InstrumentSensitivity>
            <Value>3.0E9</Value>
            <InputUnits><Name>m/s</Name></InputUnits>
          </InstrumentSensitivity>
          <Stage number="1">
            <PolesZeros>
              <PzTransferFunctionType>LAPLACE (RADIANS/SECOND)</PzTransferFunctionType>
              <NormalizationFactor>1.0</NormalizationFactor>
              <Zero number="0"><Real>0.0</Real><Imaginary>0.0</Imaginary></Zero>
              <Pole number="0"><Real>-3.0</Real><Imaginary>0.0</Imaginary></Pole>
            </PolesZeros>
            <Decimation><InputSampleRate>40.0</InputSampleRate><Factor>1</Factor></Decimation>
            <StageGain><Value>1.0</Value><Frequency>1.0</Frequency></StageGain>
          </Stage>
        </Response>
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""


def _station_block(station: str, sensitivity: str, pole: str) -> str:
    return f"""\
    <Station code="{station}">
      <Channel code="BHZ" locationCode="00" startDate="2000-01-01T00:00:00.0000">
        <Response>
          <InstrumentSensitivity>
            <Value>{sensitivity}</Value>
            <InputUnits><Name>m/s</Name></InputUnits>
          </InstrumentSensitivity>
          <Stage number="1">
            <PolesZeros>
              <PzTransferFunctionType>LAPLACE (RADIANS/SECOND)</PzTransferFunctionType>
              <NormalizationFactor>1.0</NormalizationFactor>
              <Zero number="0"><Real>0.0</Real><Imaginary>0.0</Imaginary></Zero>
              <Pole number="0"><Real>{pole}</Real><Imaginary>0.0</Imaginary></Pole>
            </PolesZeros>
            <Decimation><InputSampleRate>40.0</InputSampleRate><Factor>1</Factor></Decimation>
            <StageGain><Value>1.0</Value><Frequency>1.0</Frequency></StageGain>
          </Stage>
        </Response>
      </Channel>
    </Station>
"""


def _document(*networks: str) -> bytes:
    body = "".join(networks)
    return (
        '<?xml version="1.0"?>\n'
        '<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">\n'
        f"{body}"
        "</FDSNStationXML>\n"
    ).encode()


def _network_block(network: str, *station_blocks: str) -> str:
    return (
        f'  <Network code="{network}">\n' + "".join(station_blocks) + "  </Network>\n"
    )


# Two networks sharing the same station/location/channel codes -- only
# `network` disambiguates.
MULTIPLE_NETWORKS = _document(
    _network_block("IU", _station_block("ANMO", "1.0E9", "-1.0")),
    _network_block("II", _station_block("ANMO", "2.0E9", "-2.0")),
)

# One network, two stations sharing the same location/channel codes -- only
# `station` disambiguates.
MULTIPLE_STATIONS = _document(
    _network_block(
        "IU",
        _station_block("ANMO", "1.0E9", "-1.0"),
        _station_block("COLA", "2.0E9", "-2.0"),
    )
)


class TestFromBytes:
    def test_single_epoch_fixture(self) -> None:
        response = StationXMLResponse.from_bytes(
            SINGLE_EPOCH_FIXTURE.read_bytes(), time=pd.Timestamp("2016-01-01T00:00:00Z")
        )

        assert isinstance(response, Response)
        assert isinstance(response, StagedResponse)
        assert response.network == "IU"
        assert response.station == "ANMO"
        assert response.location == "00"
        assert response.channel == "BHZ"
        assert response.input_units == "m/s"
        assert len(response.stages) == 2

    def test_reference_sensitivity_excludes_a0(self) -> None:
        """reference_sensitivity must be the plain InstrumentSensitivity
        value, distinct from overall_sensitivity (which has the analog
        stage's A0 normalisation factor folded in) — otherwise
        remove_response's sensitivity-only path mis-scales by A0."""
        response = StationXMLResponse.from_bytes(
            SINGLE_EPOCH_FIXTURE.read_bytes(), time=pd.Timestamp("2016-01-01T00:00:00Z")
        )

        assert response.reference_sensitivity is not None
        assert response.reference_sensitivity != response.overall_sensitivity
        assert response.reference_sensitivity == pytest.approx(3.40413e9)

    def test_selects_currently_open_epoch(self) -> None:
        response = StationXMLResponse.from_bytes(BULK_FIXTURE.read_bytes())

        assert isinstance(response, StagedResponse)
        assert len(response.poles) == 13
        assert len(response.stages) == 2

    def test_selects_historical_epoch_by_time(self) -> None:
        response = StationXMLResponse.from_bytes(
            BULK_FIXTURE.read_bytes(), time=pd.Timestamp("1999-01-01T00:00:00Z")
        )

        assert isinstance(response, StagedResponse)
        assert len(response.stages) == 5

    def test_no_matching_epoch_raises(self) -> None:
        with pytest.raises(ValueError, match="found 0"):
            StationXMLResponse.from_bytes(
                BULK_FIXTURE.read_bytes(), time=pd.Timestamp("1990-01-01T00:00:00Z")
            )

    def test_overlapping_epochs_raise(self) -> None:
        with pytest.raises(ValueError, match="found 2"):
            StationXMLResponse.from_bytes(
                OVERLAPPING_EPOCHS, time=pd.Timestamp("2010-01-01T00:00:00Z")
            )

    def test_multiple_channels_raises_without_narrowing(self) -> None:
        # A station-level document (or one saved offline for later parsing)
        # commonly covers every location/channel on record, not just one --
        # without location/channel narrowing this is as ambiguous as
        # overlapping epochs.
        with pytest.raises(ValueError, match="found 3"):
            StationXMLResponse.from_bytes(MULTIPLE_LOCATIONS_AND_CHANNELS)

    def test_channel_alone_narrows_but_may_still_be_ambiguous(self) -> None:
        with pytest.raises(ValueError, match="found 2"):
            StationXMLResponse.from_bytes(
                MULTIPLE_LOCATIONS_AND_CHANNELS, channel="BHZ"
            )

    def test_location_and_channel_narrow_to_one_epoch(self) -> None:
        response = StationXMLResponse.from_bytes(
            MULTIPLE_LOCATIONS_AND_CHANNELS, location="10", channel="BHZ"
        )

        assert response.location == "10"
        assert response.channel == "BHZ"
        assert response.reference_sensitivity == pytest.approx(3.0e9)

    def test_multiple_networks_raise_without_network_narrowing(self) -> None:
        with pytest.raises(ValueError, match="found 2"):
            StationXMLResponse.from_bytes(MULTIPLE_NETWORKS)

    def test_network_narrows_to_one_epoch(self) -> None:
        response = StationXMLResponse.from_bytes(MULTIPLE_NETWORKS, network="II")

        assert response.network == "II"
        assert response.station == "ANMO"
        assert response.reference_sensitivity == pytest.approx(2.0e9)

    def test_multiple_stations_raise_without_station_narrowing(self) -> None:
        with pytest.raises(ValueError, match="found 2"):
            StationXMLResponse.from_bytes(MULTIPLE_STATIONS)

    def test_station_narrows_to_one_epoch(self) -> None:
        response = StationXMLResponse.from_bytes(MULTIPLE_STATIONS, station="COLA")

        assert response.station == "COLA"
        assert response.reference_sensitivity == pytest.approx(2.0e9)

    def test_error_message_lists_network_and_station_narrowing(self) -> None:
        with pytest.raises(ValueError, match="network 'XX', station 'YY'"):
            StationXMLResponse.from_bytes(MULTIPLE_NETWORKS, network="XX", station="YY")


class TestAllFromBytes:
    def test_real_bulk_fixture(self) -> None:
        responses = StationXMLResponse.all_from_bytes(BULK_FIXTURE.read_bytes())
        assert len(responses) == 9
        for response in responses:
            assert isinstance(response, Response)
            assert isinstance(response, StagedResponse)
            assert response.network == "IU"
            assert response.station == "ANMO"
        for previous, current in zip(responses, responses[1:]):
            assert previous.end_date == current.start_date
        assert responses[-1].end_date is None

    def test_single_epoch_still_returns_a_list(self) -> None:
        responses = StationXMLResponse.all_from_bytes(SINGLE_EPOCH_FIXTURE.read_bytes())
        assert len(responses) == 1


class TestFetch:
    @pytest.fixture()
    def station(self) -> MiniStation:
        return MiniStation(
            name="ANMO",
            network="IU",
            location="00",
            channel="LHZ",
            latitude=34.945981,
            longitude=-106.457133,
        )

    def test_single_epoch_fixture(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        calls: list[tuple[str, dict[str, object]]] = []

        def fake_http_get(
            url: str, fields: dict[str, object], **kwargs: object
        ) -> bytes:
            calls.append((url, fields))
            return SINGLE_EPOCH_FIXTURE.read_bytes()

        monkeypatch.setattr("pysmo.tools.web.http_get", fake_http_get)

        response = StationXMLResponse.fetch(
            station=station, time=pd.Timestamp("2016-01-01T00:00:00Z")
        )

        assert isinstance(response, Response)
        assert isinstance(response, StagedResponse)
        assert response.input_units == "m/s"
        assert len(response.stages) == 2

        _, fields = calls[0]
        assert fields["net"] == "IU"
        assert fields["sta"] == "ANMO"
        assert fields["loc"] == "00"
        assert fields["cha"] == "LHZ"
        assert fields["level"] == "response"

    def test_selects_currently_open_epoch(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        monkeypatch.setattr(
            "pysmo.tools.web.http_get",
            lambda *args, **kwargs: BULK_FIXTURE.read_bytes(),
        )

        response = StationXMLResponse.fetch(station=station)

        assert isinstance(response, StagedResponse)
        assert len(response.poles) == 13
        assert len(response.stages) == 2

    def test_selects_historical_epoch_by_time(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        monkeypatch.setattr(
            "pysmo.tools.web.http_get",
            lambda *args, **kwargs: BULK_FIXTURE.read_bytes(),
        )

        response = StationXMLResponse.fetch(
            station=station, time=pd.Timestamp("1999-01-01T00:00:00Z")
        )

        assert isinstance(response, StagedResponse)
        assert len(response.stages) == 5

    def test_no_matching_epoch_raises(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        monkeypatch.setattr(
            "pysmo.tools.web.http_get",
            lambda *args, **kwargs: BULK_FIXTURE.read_bytes(),
        )

        with pytest.raises(ValueError, match="found 0"):
            StationXMLResponse.fetch(
                station=station, time=pd.Timestamp("1990-01-01T00:00:00Z")
            )

    def test_overlapping_epochs_raise(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        monkeypatch.setattr(
            "pysmo.tools.web.http_get",
            lambda *args, **kwargs: OVERLAPPING_EPOCHS,
        )

        with pytest.raises(ValueError, match="found 2"):
            StationXMLResponse.fetch(
                station=station, time=pd.Timestamp("2010-01-01T00:00:00Z")
            )
