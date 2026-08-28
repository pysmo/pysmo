"""Tests for pysmo.classes.StationXML."""

from pathlib import Path

import pandas as pd
import pytest

from pysmo import Location, MiniStation, Response, StagedResponse, Station
from pysmo.classes import StationXML, resolve_epochs

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
      <Latitude>34.9</Latitude><Longitude>-106.5</Longitude>
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
      <Latitude>34.9</Latitude><Longitude>-106.5</Longitude>
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
      <Latitude>0.0</Latitude><Longitude>0.0</Longitude>
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
        epoch = StationXML.from_bytes(
            SINGLE_EPOCH_FIXTURE.read_bytes(), time=pd.Timestamp("2016-01-01T00:00:00Z")
        )

        assert isinstance(epoch, Station)
        assert isinstance(epoch, Location)
        assert epoch.network == "IU"
        assert epoch.name == "ANMO"
        assert epoch.location == "00"
        assert epoch.channel == "BHZ"
        assert epoch.latitude == pytest.approx(34.94591)

        response = epoch.response
        assert isinstance(response, Response)
        assert isinstance(response, StagedResponse)
        assert response.input_units == "m/s"
        assert len(response.stages) == 2

    def test_reference_sensitivity_excludes_a0(self) -> None:
        """reference_sensitivity must be the plain InstrumentSensitivity
        value, distinct from overall_sensitivity (which has the analog
        stage's A0 normalisation factor folded in) — otherwise
        remove_response's sensitivity-only path mis-scales by A0."""
        response = StationXML.from_bytes(
            SINGLE_EPOCH_FIXTURE.read_bytes(), time=pd.Timestamp("2016-01-01T00:00:00Z")
        ).response

        assert response.reference_sensitivity is not None
        assert response.reference_sensitivity != response.overall_sensitivity
        assert response.reference_sensitivity == pytest.approx(3.40413e9)

    def test_selects_currently_open_epoch(self) -> None:
        response = StationXML.from_bytes(BULK_FIXTURE.read_bytes()).response

        assert isinstance(response, StagedResponse)
        assert len(response.poles) == 13
        assert len(response.stages) == 2

    def test_selects_historical_epoch_by_time(self) -> None:
        response = StationXML.from_bytes(
            BULK_FIXTURE.read_bytes(), time=pd.Timestamp("1999-01-01T00:00:00Z")
        ).response

        assert isinstance(response, StagedResponse)
        assert len(response.stages) == 5

    def test_no_matching_epoch_raises(self) -> None:
        with pytest.raises(ValueError, match="found 0"):
            StationXML.from_bytes(
                BULK_FIXTURE.read_bytes(), time=pd.Timestamp("1990-01-01T00:00:00Z")
            )

    def test_overlapping_epochs_raise(self) -> None:
        with pytest.raises(ValueError, match="found 2"):
            StationXML.from_bytes(
                OVERLAPPING_EPOCHS, time=pd.Timestamp("2010-01-01T00:00:00Z")
            )

    def test_multiple_channels_raises_without_narrowing(self) -> None:
        # A station-level document (or one saved offline for later parsing)
        # commonly covers every location/channel on record, not just one --
        # without location/channel narrowing this is as ambiguous as
        # overlapping epochs.
        with pytest.raises(ValueError, match="found 3"):
            StationXML.from_bytes(MULTIPLE_LOCATIONS_AND_CHANNELS)

    def test_channel_alone_narrows_but_may_still_be_ambiguous(self) -> None:
        with pytest.raises(ValueError, match="found 2"):
            StationXML.from_bytes(MULTIPLE_LOCATIONS_AND_CHANNELS, channel="BHZ")

    def test_location_and_channel_narrow_to_one_epoch(self) -> None:
        epoch = StationXML.from_bytes(
            MULTIPLE_LOCATIONS_AND_CHANNELS, location="10", channel="BHZ"
        )

        assert epoch.location == "10"
        assert epoch.channel == "BHZ"
        assert epoch.response.reference_sensitivity == pytest.approx(3.0e9)

    def test_multiple_networks_raise_without_network_narrowing(self) -> None:
        with pytest.raises(ValueError, match="found 2"):
            StationXML.from_bytes(MULTIPLE_NETWORKS)

    def test_network_narrows_to_one_epoch(self) -> None:
        epoch = StationXML.from_bytes(MULTIPLE_NETWORKS, network="II")

        assert epoch.network == "II"
        assert epoch.name == "ANMO"
        assert epoch.response.reference_sensitivity == pytest.approx(2.0e9)

    def test_multiple_stations_raise_without_station_narrowing(self) -> None:
        with pytest.raises(ValueError, match="found 2"):
            StationXML.from_bytes(MULTIPLE_STATIONS)

    def test_station_narrows_to_one_epoch(self) -> None:
        epoch = StationXML.from_bytes(MULTIPLE_STATIONS, station="COLA")

        assert epoch.name == "COLA"
        assert epoch.response.reference_sensitivity == pytest.approx(2.0e9)

    def test_error_message_lists_network_and_station_narrowing(self) -> None:
        with pytest.raises(ValueError, match="network 'XX', station 'YY'"):
            StationXML.from_bytes(MULTIPLE_NETWORKS, network="XX", station="YY")


class TestAllFromBytes:
    def test_real_bulk_fixture(self) -> None:
        epochs = StationXML.all_from_bytes(BULK_FIXTURE.read_bytes())
        assert len(epochs) == 9
        for epoch in epochs:
            assert isinstance(epoch, Station)
            assert isinstance(epoch.response, StagedResponse)
            assert epoch.network == "IU"
            assert epoch.name == "ANMO"
        for previous, current in zip(epochs, epochs[1:]):
            assert previous.end_date == current.start_date
        assert epochs[-1].end_date is None

    def test_single_epoch_still_returns_a_list(self) -> None:
        epochs = StationXML.all_from_bytes(SINGLE_EPOCH_FIXTURE.read_bytes())
        assert len(epochs) == 1


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

        epoch = StationXML.fetch(
            station=station, time=pd.Timestamp("2016-01-01T00:00:00Z")
        )

        assert isinstance(epoch, Station)
        response = epoch.response
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

        response = StationXML.fetch(station=station).response

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

        response = StationXML.fetch(
            station=station, time=pd.Timestamp("1999-01-01T00:00:00Z")
        ).response

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
            StationXML.fetch(station=station, time=pd.Timestamp("1990-01-01T00:00:00Z"))

    def test_overlapping_epochs_raise(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        monkeypatch.setattr(
            "pysmo.tools.web.http_get",
            lambda *args, **kwargs: OVERLAPPING_EPOCHS,
        )

        with pytest.raises(ValueError, match="found 2"):
            StationXML.fetch(station=station, time=pd.Timestamp("2010-01-01T00:00:00Z"))


_MULTI = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO" startDate="1989-01-01T00:00:00">
      <Latitude>34.9</Latitude><Longitude>-106.4</Longitude><Elevation>1800</Elevation>
      <Channel code="BHZ" locationCode="00" startDate="2000-01-01T00:00:00"
               endDate="2010-01-01T00:00:00">
        <Latitude>34.9</Latitude><Longitude>-106.4</Longitude><Elevation>1700</Elevation>
      </Channel>
      <Channel code="BHZ" locationCode="00" startDate="2010-01-01T00:00:00">
        <Latitude>34.9</Latitude><Longitude>-106.4</Longitude><Elevation>1650</Elevation>
      </Channel>
      <Channel code="BH1" locationCode="00" startDate="2000-01-01T00:00:00">
        <Latitude>34.9</Latitude><Longitude>-106.4</Longitude><Elevation>1700</Elevation>
      </Channel>
    </Station>
  </Network>
  <Network code="II">
    <Station code="BFO" startDate="1996-01-01T00:00:00">
      <Latitude>48.3</Latitude><Longitude>8.3</Longitude><Elevation>590</Elevation>
      <Channel code="BHZ" locationCode="00" startDate="1996-01-01T00:00:00"/>
    </Station>
  </Network>
</FDSNStationXML>
"""

_OVERLAPPING_STATION_EPOCHS = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO" startDate="1989-01-01T00:00:00">
      <Latitude>34.9</Latitude><Longitude>-106.4</Longitude>
      <Channel code="BHZ" locationCode="00" startDate="2000-01-01T00:00:00"
               endDate="2015-01-01T00:00:00">
        <Latitude>34.9</Latitude><Longitude>-106.4</Longitude>
      </Channel>
      <Channel code="BHZ" locationCode="00" startDate="2005-01-01T00:00:00"
               endDate="2020-01-01T00:00:00">
        <Latitude>34.9</Latitude><Longitude>-106.4</Longitude>
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""

_T2010 = pd.Timestamp("2010-06-01T00:00:00Z")


def _epoch(
    network: str, name: str, channel: str, start: str, end: str | None
) -> StationXML:
    return StationXML(
        network=network,
        name=name,
        location="00",
        channel=channel,
        latitude=0.0,
        longitude=0.0,
        start_date=start,
        end_date=end,
    )


class TestResolveEpochs:
    def test_collapses_each_nslc_to_covering_epoch(self) -> None:
        epochs = [
            _epoch("IU", "ANMO", "BHZ", "2000-01-01", "2010-01-01"),
            _epoch("IU", "ANMO", "BHZ", "2010-01-01", None),
            _epoch("IU", "COLA", "BHZ", "2005-01-01", None),
        ]
        resolved = resolve_epochs(epochs, _T2010)
        assert {(e.name, e.start_date.year) for e in resolved} == {
            ("ANMO", 2010),
            ("COLA", 2005),
        }

    def test_drops_nslc_with_no_covering_epoch(self) -> None:
        epochs = [_epoch("IU", "ANMO", "BHZ", "2015-01-01", None)]
        assert resolve_epochs(epochs, _T2010) == []

    def test_raises_on_overlapping_epochs(self) -> None:
        epochs = [
            _epoch("IU", "ANMO", "BHZ", "2000-01-01", "2015-01-01"),
            _epoch("IU", "ANMO", "BHZ", "2005-01-01", "2020-01-01"),
        ]
        with pytest.raises(ValueError, match="2 epochs covering"):
            resolve_epochs(epochs, _T2010)


class TestNarrowingWorkflow:
    """The `stations_from_stationxml` convenience was dropped — narrowing is
    now explicit: parse to a flat list, filter by comprehension, resolve."""

    def test_channel_filter_then_resolve_selects_historical_epoch(self) -> None:
        epochs = StationXML.all_from_bytes(_MULTI)
        bhz = [e for e in epochs if e.channel == "BHZ"]
        resolved = resolve_epochs(bhz, _T2010)
        anmo = next(e for e in resolved if e.name == "ANMO")
        assert anmo.start_date == pd.Timestamp("2010-01-01T00:00:00Z")

    def test_network_filter(self) -> None:
        epochs = StationXML.all_from_bytes(_MULTI)
        assert {e.network for e in epochs if e.channel == "BHZ"} == {"IU", "II"}
        ii = [e for e in epochs if e.network == "II" and e.channel == "BHZ"]
        assert ii[0].name == "BFO"

    def test_nslc_with_no_covering_epoch_dropped(self) -> None:
        epochs = StationXML.all_from_bytes(_MULTI)
        bhz = [e for e in epochs if e.channel == "BHZ"]
        assert resolve_epochs(bhz, pd.Timestamp("1990-01-01T00:00:00Z")) == []

    def test_overlapping_document_epochs_raise(self) -> None:
        epochs = StationXML.all_from_bytes(_OVERLAPPING_STATION_EPOCHS)
        with pytest.raises(ValueError, match="epochs covering"):
            resolve_epochs(epochs, _T2010)
