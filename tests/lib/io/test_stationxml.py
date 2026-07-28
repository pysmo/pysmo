"""Tests for pysmo.lib.io._stationxml."""

from pathlib import Path

import pandas as pd
import pytest

from pysmo.lib.io._stationxml import parse_stationxml

SINGLE_EPOCH_FIXTURE = Path(__file__).parent / "stationxml_anmo_single.xml"
BULK_FIXTURE = Path(__file__).parent / "stationxml_anmo_bulk.xml"
FIR_STAGE_FIXTURE = Path(__file__).parent / "stationxml_fir_stage.xml"

MINIMAL_ONE_STAGE = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00" startDate="2018-07-09T20:45:00.0000">
        <Response>
          <InstrumentSensitivity>
            <Value>1.98475E9</Value>
            <Frequency>0.02</Frequency>
            <InputUnits><Name>m/s</Name></InputUnits>
            <OutputUnits><Name>counts</Name></OutputUnits>
          </InstrumentSensitivity>
          <Stage number="1">
            <PolesZeros>
              <InputUnits><Name>m/s</Name></InputUnits>
              <OutputUnits><Name>V</Name></OutputUnits>
              <PzTransferFunctionType>LAPLACE (RADIANS/SECOND)</PzTransferFunctionType>
              <NormalizationFactor>5.03773E14</NormalizationFactor>
              <NormalizationFrequency>0.02</NormalizationFrequency>
              <Zero number="0"><Real>0.0</Real><Imaginary>0.0</Imaginary></Zero>
              <Pole number="0"><Real>-0.037</Real><Imaginary>0.037</Imaginary></Pole>
            </PolesZeros>
            <Decimation>
              <InputSampleRate>40.0</InputSampleRate>
              <Factor>1</Factor>
            </Decimation>
            <StageGain><Value>1183.0</Value><Frequency>0.02</Frequency></StageGain>
          </Stage>
        </Response>
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""


def _replace(template: bytes, old: str, new: str) -> bytes:
    return template.replace(old.encode(), new.encode())


class TestParseStationxml:
    def test_real_single_epoch_fixture_with_coefficients_stages(self) -> None:
        responses = parse_stationxml(SINGLE_EPOCH_FIXTURE.read_bytes())
        assert len(responses) == 1
        response = responses[0]

        assert response.network == "IU"
        assert response.station == "ANMO"
        assert response.location == "00"
        assert response.channel == "BHZ"
        assert response.start_date == pd.Timestamp("2014-12-17T18:40:00Z")
        assert response.end_date == pd.Timestamp("2018-07-09T20:45:00Z")
        assert response.sensitivity_input_units == "m/s"
        assert response.sensitivity_value == pytest.approx(3.40413e9)
        assert len(response.poles) == 5
        assert len(response.zeros) == 2
        assert len(response.digital_stages) == 2

        for stage in response.digital_stages:
            # Unit-gain at DC per the parse-time normalisation convention.
            assert sum(stage.numerator) / sum(stage.denominator) == pytest.approx(1.0)

        assert response.digital_stages[0].correction == 0.0
        assert response.digital_stages[1].correction == pytest.approx(1.6305)

    def test_real_bulk_fixture_returns_one_entry_per_epoch(self) -> None:
        responses = parse_stationxml(BULK_FIXTURE.read_bytes())
        assert len(responses) == 9

        # Epochs are contiguous and in document order; only the last is open.
        for previous, current in zip(responses, responses[1:]):
            assert previous.end_date == current.start_date
        assert responses[-1].end_date is None
        assert {response.network for response in responses} == {"IU"}
        assert {response.station for response in responses} == {"ANMO"}
        assert {response.channel for response in responses} == {"BHZ"}

    def test_only_one_stage_no_digital_stages(self) -> None:
        responses = parse_stationxml(MINIMAL_ONE_STAGE)
        assert len(responses) == 1
        assert responses[0].digital_stages == []
        assert len(responses[0].poles) == 1
        assert len(responses[0].zeros) == 1

    def test_fir_stage_shape(self) -> None:
        responses = parse_stationxml(FIR_STAGE_FIXTURE.read_bytes())
        assert len(responses) == 1
        response = responses[0]
        assert len(response.digital_stages) == 1
        stage = response.digital_stages[0]
        assert stage.input_sample_rate == 100.0
        assert stage.decimation_factor == 2
        assert stage.denominator == [1.0]
        assert len(stage.numerator) == 3
        assert sum(stage.numerator) == pytest.approx(1.0)
        assert stage.correction == pytest.approx(0.01)

    def test_fir_stage_with_no_coefficients_is_harmless_identity_stage(self) -> None:
        # Mirrors the no-coefficients <Coefficients> case (a pure scalar-gain
        # "stage" rather than an actual filter) -- must not raise.
        xml = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00" startDate="2018-07-09T20:45:00.0000">
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
          </Stage>
          <Stage number="2">
            <FIR>
              <Symmetry>NONE</Symmetry>
            </FIR>
            <Decimation><InputSampleRate>40.0</InputSampleRate><Factor>1</Factor></Decimation>
          </Stage>
        </Response>
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""
        responses = parse_stationxml(xml)
        assert len(responses) == 1
        stage = responses[0].digital_stages[0]
        assert stage.numerator == [1.0]
        assert stage.denominator == [1.0]

    @staticmethod
    def _fir_xml(symmetry: str) -> bytes:
        return f"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00" startDate="2018-07-09T20:45:00.0000">
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
          </Stage>
          <Stage number="2">
            <FIR>
              <Symmetry>{symmetry}</Symmetry>
              <NumeratorCoefficient i="0">0.1</NumeratorCoefficient>
              <NumeratorCoefficient i="1">0.4</NumeratorCoefficient>
              <NumeratorCoefficient i="2">0.5</NumeratorCoefficient>
            </FIR>
            <Decimation><InputSampleRate>40.0</InputSampleRate><Factor>1</Factor></Decimation>
          </Stage>
        </Response>
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
""".encode()

    def test_fir_stage_coefficients_sorted_by_i_not_document_order(self) -> None:
        # FDSN StationXML indexes <NumeratorCoefficient> by the "i" attribute
        # (not "number", unlike <Numerator>/<Denominator> under <Coefficients>
        # -- see the FDSN XSD's FIRType). Listing entries out of document
        # order here checks they are sorted by "i", not left in document
        # order.
        xml = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00" startDate="2018-07-09T20:45:00.0000">
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
          </Stage>
          <Stage number="2">
            <FIR>
              <Symmetry>NONE</Symmetry>
              <NumeratorCoefficient i="2">0.3</NumeratorCoefficient>
              <NumeratorCoefficient i="0">0.1</NumeratorCoefficient>
              <NumeratorCoefficient i="1">0.2</NumeratorCoefficient>
            </FIR>
            <Decimation><InputSampleRate>40.0</InputSampleRate><Factor>1</Factor></Decimation>
          </Stage>
        </Response>
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""
        responses = parse_stationxml(xml)
        numerator = responses[0].digital_stages[0].numerator

        # Sorted by "i" (0.1, 0.2, 0.3), then normalised to sum to 1.
        assert numerator == pytest.approx([1 / 6, 2 / 6, 3 / 6])

    def test_fir_stage_odd_symmetry_mirrors_coefficients(self) -> None:
        # FDSN's own worked example: ODD [0.1, 0.4, 0.5] -> [0.1, 0.4, 0.5, 0.4, 0.1]
        # (mirrored about a shared centre tap, giving an odd total length).
        responses = parse_stationxml(self._fir_xml("ODD"))
        numerator = responses[0].digital_stages[0].numerator

        assert len(numerator) == 5
        assert numerator == numerator[::-1]
        assert sum(numerator) == pytest.approx(1.0)

    def test_fir_stage_even_symmetry_mirrors_coefficients(self) -> None:
        # FDSN's own worked example: EVEN [0.1, 0.4, 0.5] -> [0.1, 0.4, 0.5, 0.5,
        # 0.4, 0.1] (mirrored with no shared centre tap, giving an even length).
        responses = parse_stationxml(self._fir_xml("EVEN"))
        numerator = responses[0].digital_stages[0].numerator

        assert len(numerator) == 6
        assert numerator == numerator[::-1]
        assert sum(numerator) == pytest.approx(1.0)

    def test_fir_stage_unsupported_symmetry_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported FIR Symmetry"):
            parse_stationxml(self._fir_xml("BOGUS"))

    def test_correction_defaults_to_zero_when_absent(self) -> None:
        xml = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00" startDate="2018-07-09T20:45:00.0000">
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
          </Stage>
          <Stage number="2">
            <Coefficients>
              <CfTransferFunctionType>DIGITAL</CfTransferFunctionType>
              <Numerator>1.0</Numerator>
            </Coefficients>
            <Decimation><InputSampleRate>40.0</InputSampleRate><Factor>1</Factor></Decimation>
          </Stage>
        </Response>
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""
        responses = parse_stationxml(xml)
        assert responses[0].digital_stages[0].correction == 0.0

    def test_doctype_declaration_raises(self) -> None:
        xml = b"""\
<?xml version="1.0"?>
<!DOCTYPE FDSNStationXML [<!ENTITY x "boom">]>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00" startDate="2018-07-09T20:45:00.0000">
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""
        with pytest.raises(ValueError, match="DOCTYPE"):
            parse_stationxml(xml)

    def test_missing_response_element_raises(self) -> None:
        xml = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00" startDate="2018-07-09T20:45:00.0000">
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""
        with pytest.raises(ValueError, match="no <Response> element"):
            parse_stationxml(xml)

    def test_missing_instrument_sensitivity_raises(self) -> None:
        xml = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00" startDate="2018-07-09T20:45:00.0000">
        <Response></Response>
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""
        with pytest.raises(ValueError, match="InstrumentSensitivity"):
            parse_stationxml(xml)

    def test_missing_analog_stage_raises(self) -> None:
        xml = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00" startDate="2018-07-09T20:45:00.0000">
        <Response>
          <InstrumentSensitivity>
            <Value>1.0E9</Value>
            <InputUnits><Name>m/s</Name></InputUnits>
          </InstrumentSensitivity>
        </Response>
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""
        with pytest.raises(ValueError, match="analog PolesZeros stage"):
            parse_stationxml(xml)

    def test_unrecognised_digital_polezeros_type_raises(self) -> None:
        xml = _replace(
            MINIMAL_ONE_STAGE,
            "LAPLACE (RADIANS/SECOND)",
            "DIGITAL (Z-TRANSFORM)",
        )
        with pytest.raises(ValueError, match="Unsupported PzTransferFunctionType"):
            parse_stationxml(xml)

    def test_unrecognised_coefficients_transfer_function_type_raises(self) -> None:
        xml = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00" startDate="2018-07-09T20:45:00.0000">
        <Response>
          <InstrumentSensitivity>
            <Value>1.0E9</Value>
            <InputUnits><Name>m/s</Name></InputUnits>
          </InstrumentSensitivity>
          <Stage number="1">
            <Coefficients>
              <CfTransferFunctionType>ANALOG (RADIANS/SECOND)</CfTransferFunctionType>
              <Numerator number="0">1.0</Numerator>
            </Coefficients>
            <Decimation><InputSampleRate>40.0</InputSampleRate><Factor>1</Factor></Decimation>
          </Stage>
        </Response>
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""
        with pytest.raises(ValueError, match="Unsupported CfTransferFunctionType"):
            parse_stationxml(xml)

    def test_stage_missing_decimation_raises(self) -> None:
        xml = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00" startDate="2018-07-09T20:45:00.0000">
        <Response>
          <InstrumentSensitivity>
            <Value>1.0E9</Value>
            <InputUnits><Name>m/s</Name></InputUnits>
          </InstrumentSensitivity>
          <Stage number="1">
            <Coefficients>
              <CfTransferFunctionType>DIGITAL</CfTransferFunctionType>
              <Numerator number="0">1.0</Numerator>
            </Coefficients>
          </Stage>
        </Response>
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""
        with pytest.raises(ValueError, match="no <Decimation> element"):
            parse_stationxml(xml)

    def test_analog_stage_missing_pz_transfer_function_type_raises(self) -> None:
        xml = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00" startDate="2018-07-09T20:45:00.0000">
        <Response>
          <InstrumentSensitivity>
            <Value>1.0E9</Value>
            <InputUnits><Name>m/s</Name></InputUnits>
          </InstrumentSensitivity>
          <Stage number="1">
            <PolesZeros>
              <NormalizationFactor>1.0</NormalizationFactor>
              <Zero number="0"><Real>0.0</Real><Imaginary>0.0</Imaginary></Zero>
              <Pole number="0"><Real>-1.0</Real><Imaginary>0.0</Imaginary></Pole>
            </PolesZeros>
            <Decimation><InputSampleRate>40.0</InputSampleRate><Factor>1</Factor></Decimation>
          </Stage>
        </Response>
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""
        with pytest.raises(
            ValueError, match="Missing required <PzTransferFunctionType>"
        ):
            parse_stationxml(xml)

    def test_digital_stage_zero_gain_coefficients_raises(self) -> None:
        xml = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00" startDate="2018-07-09T20:45:00.0000">
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
          </Stage>
          <Stage number="2">
            <Coefficients>
              <CfTransferFunctionType>DIGITAL</CfTransferFunctionType>
              <Numerator number="0">1.0</Numerator>
              <Numerator number="1">-1.0</Numerator>
            </Coefficients>
            <Decimation><InputSampleRate>40.0</InputSampleRate><Factor>1</Factor></Decimation>
          </Stage>
        </Response>
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""
        with pytest.raises(ValueError, match="coefficients sum to 0"):
            parse_stationxml(xml)

    def test_stage_with_no_recognised_element_raises(self) -> None:
        xml = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00" startDate="2018-07-09T20:45:00.0000">
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
          </Stage>
          <Stage number="2">
            <Decimation><InputSampleRate>40.0</InputSampleRate><Factor>1</Factor></Decimation>
          </Stage>
        </Response>
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""
        with pytest.raises(
            ValueError, match="no recognised PolesZeros/Coefficients/FIR"
        ):
            parse_stationxml(xml)

    def test_gain_only_stage_is_skipped(self) -> None:
        """A `<Stage>` with only `<StageGain>` and no PolesZeros/Coefficients/
        FIR/Decimation is a pure scalar-gain stage (e.g. an analog amplifier
        between the sensor and digitiser) — a common, valid construct that
        contributes no frequency-dependent behaviour and is already folded
        into InstrumentSensitivity, so it should be skipped rather than
        raise or be recorded as a digital stage."""
        xml = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00" startDate="2018-07-09T20:45:00.0000">
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
          </Stage>
          <Stage number="2">
            <StageGain><Value>1.0</Value><Frequency>1.0</Frequency></StageGain>
          </Stage>
        </Response>
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""
        responses = parse_stationxml(xml)
        assert len(responses) == 1
        assert responses[0].digital_stages == []

    def test_instrument_sensitivity_missing_input_units_raises(self) -> None:
        xml = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00" startDate="2018-07-09T20:45:00.0000">
        <Response>
          <InstrumentSensitivity>
            <Value>1.0E9</Value>
          </InstrumentSensitivity>
        </Response>
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""
        with pytest.raises(
            ValueError, match="InstrumentSensitivity has no <InputUnits>"
        ):
            parse_stationxml(xml)

    def test_multiple_analog_stages_are_cascaded(self) -> None:
        # Cascaded analog stages are valid FDSN StationXML -- e.g. a sensor
        # (stage 1) followed by an analog preamplifier, which the spec's own
        # recommended practice encodes as a gain-only PolesZeros stage (no
        # poles/zeros, NormalizationFactor=1). Poles-and-zeros representations
        # multiply in the s-domain, so poles/zeros concatenate and
        # normalization factors multiply.
        xml = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00" startDate="2018-07-09T20:45:00.0000">
        <Response>
          <InstrumentSensitivity>
            <Value>1.0E9</Value>
            <InputUnits><Name>m/s</Name></InputUnits>
          </InstrumentSensitivity>
          <Stage number="1">
            <PolesZeros>
              <PzTransferFunctionType>LAPLACE (RADIANS/SECOND)</PzTransferFunctionType>
              <NormalizationFactor>2.0</NormalizationFactor>
              <Zero number="0"><Real>0.0</Real><Imaginary>0.0</Imaginary></Zero>
              <Pole number="0"><Real>-1.0</Real><Imaginary>0.0</Imaginary></Pole>
            </PolesZeros>
            <Decimation><InputSampleRate>40.0</InputSampleRate><Factor>1</Factor></Decimation>
          </Stage>
          <Stage number="2">
            <PolesZeros>
              <PzTransferFunctionType>LAPLACE (RADIANS/SECOND)</PzTransferFunctionType>
              <NormalizationFactor>3.0</NormalizationFactor>
              <Zero number="0"><Real>1.0</Real><Imaginary>0.0</Imaginary></Zero>
              <Pole number="0"><Real>-2.0</Real><Imaginary>0.0</Imaginary></Pole>
            </PolesZeros>
            <Decimation><InputSampleRate>40.0</InputSampleRate><Factor>1</Factor></Decimation>
          </Stage>
        </Response>
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""
        responses = parse_stationxml(xml)
        assert responses[0].poles == [complex(-1.0, 0.0), complex(-2.0, 0.0)]
        assert responses[0].zeros == [complex(0.0, 0.0), complex(1.0, 0.0)]
        assert responses[0].normalization_factor == pytest.approx(6.0)

    def test_stages_sorted_by_number_not_document_order(self) -> None:
        # <Stage number="..."> (not document order) is the authoritative
        # processing sequence -- see the FDSN XSD's ResponseStageType. Listing
        # stage 2 before stage 1 here checks stages are sorted by "number",
        # not left in document order, which would otherwise load the digital
        # decimation stages backward.
        xml = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00" startDate="2018-07-09T20:45:00.0000">
        <Response>
          <InstrumentSensitivity>
            <Value>1.0E9</Value>
            <InputUnits><Name>m/s</Name></InputUnits>
          </InstrumentSensitivity>
          <Stage number="2">
            <Coefficients>
              <CfTransferFunctionType>DIGITAL</CfTransferFunctionType>
              <Numerator>0.5</Numerator>
              <Numerator>0.5</Numerator>
            </Coefficients>
            <Decimation><InputSampleRate>20.0</InputSampleRate><Factor>2</Factor></Decimation>
          </Stage>
          <Stage number="1">
            <PolesZeros>
              <PzTransferFunctionType>LAPLACE (RADIANS/SECOND)</PzTransferFunctionType>
              <NormalizationFactor>1.0</NormalizationFactor>
              <Zero number="0"><Real>0.0</Real><Imaginary>0.0</Imaginary></Zero>
              <Pole number="0"><Real>-1.0</Real><Imaginary>0.0</Imaginary></Pole>
            </PolesZeros>
            <Decimation><InputSampleRate>40.0</InputSampleRate><Factor>1</Factor></Decimation>
          </Stage>
        </Response>
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""
        responses = parse_stationxml(xml)
        digital_stages = responses[0].digital_stages
        assert len(digital_stages) == 1
        assert digital_stages[0].input_sample_rate == 20.0
        assert digital_stages[0].decimation_factor == 2

    def test_missing_start_date_raises(self) -> None:
        xml = b"""\
<?xml version="1.0"?>
<FDSNStationXML xmlns="http://www.fdsn.org/xml/station/1">
  <Network code="IU">
    <Station code="ANMO">
      <Channel code="BHZ" locationCode="00">
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
          </Stage>
        </Response>
      </Channel>
    </Station>
  </Network>
</FDSNStationXML>
"""
        with pytest.raises(ValueError, match="no startDate attribute"):
            parse_stationxml(xml)
