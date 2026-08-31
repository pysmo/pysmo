from typing import Protocol, runtime_checkable

from attrs import define, field, setters, validators

from pysmo.lib.validators import convert_to_complex_list, validate_nonzero
from pysmo.typing import NonZeroNumber, PositiveNumber

__all__ = [
    "MiniResponse",
    "MiniResponseStage",
    "MiniStagedResponse",
    "Response",
    "ResponseStage",
    "StagedResponse",
]


def _convert_float_list(value: list[float]) -> list[float]:
    """Convert an iterable of numbers to a list of `float` values."""
    return [float(item) for item in value]


def _convert_optional_float(value: float | None) -> float | None:
    """Convert `value` to `float`, passing `None` through unchanged."""
    return None if value is None else float(value)


def _convert_strict_int(value: int) -> int:
    """Convert `value` to `int`, raising if it isn't a whole number.

    Unlike a bare `int()` converter, this rejects a fractional value (e.g.
    `2.5`) instead of silently discarding its fractional part.
    """
    as_float = float(value)
    if not as_float.is_integer():
        raise ValueError(f"{value!r} is not a whole number.")
    return int(as_float)


@runtime_checkable
class Response(Protocol):
    """Protocol class to define the `Response` type.

    Represents an analog instrument response (Laplace domain), equivalent to
    a SAC PZ file: poles/zeros plus the total system sensitivity.
    """

    poles: list[complex]
    """Response poles, in radians/second (SAC PZ / `LAPLACE (RADIANS/SECOND)` convention)."""

    zeros: list[complex]
    """Response zeros, in radians/second."""

    overall_sensitivity: NonZeroNumber
    """Scale factor combined with `poles`/`zeros` to reconstruct the full,
    frequency-dependent transfer function `H(f)`.

    Equivalent to `CONSTANT` in a SAC PZ file (`A0 * sensitivity`, the
    analog stage's normalisation factor times the reference-frequency
    sensitivity), or FDSN StationXML's `NormalizationFactor *
    InstrumentSensitivity`. This is *not* the instrument's plain flat-band
    gain — see [`reference_sensitivity`][pysmo.Response.reference_sensitivity]
    for that — so dividing raw data by `overall_sensitivity` directly
    (rather than combining it with `poles`/`zeros`, or using
    `reference_sensitivity` instead) mis-scales the result by the `A0`
    factor, often several orders of magnitude.

    Negative values are permitted (but not zero): a negative `CONSTANT`/
    `NormalizationFactor` is how a reversed-polarity channel is recorded in
    the wild, not an error.
    """

    reference_sensitivity: NonZeroNumber | None
    """Total system sensitivity (counts per physical unit) at the response's
    own reference/normalisation frequency, with no `A0` normalisation folded
    in.

    Equivalent to SAC PZ's `SENSITIVITY` header value, or FDSN StationXML's
    `InstrumentSensitivity/Value`. This — not `overall_sensitivity`, which
    has `A0` folded in — is the correct divisor for a flat, zero-phase
    approximation of the response (e.g.
    [`remove_response`][pysmo.tools.signal.remove_response]'s
    sensitivity-only path). `None` if unavailable (e.g. a SAC PZ file
    without a `SENSITIVITY` header): callers needing it should raise rather
    than silently substituting `overall_sensitivity`. As with
    `overall_sensitivity`, a negative value indicates reversed polarity
    rather than an error; zero is not permitted.
    """

    input_units: str
    """Physical units produced by removing this response (e.g. `"M/S"`, `"M/S**2"`).

    Informational only: not validated against a fixed set of units, and not
    read by [`remove_response`][pysmo.tools.signal.remove_response] or
    [`integrate`][pysmo.tools.signal.integrate]/
    [`differentiate`][pysmo.tools.signal.differentiate] — callers are
    responsible for interpreting it themselves.
    """


@runtime_checkable
class ResponseStage(Protocol):
    """Protocol class to define one digital (FIR/IIR) decimation stage."""

    input_sample_rate: PositiveNumber
    """Sample rate (Hz) this stage's filter coefficients operate at."""

    decimation_factor: int
    """Integer decimation factor applied by this stage."""

    numerator: list[float]
    """Feedforward ("b") filter coefficients."""

    denominator: list[float]
    """Feedback ("a") filter coefficients. `[1.0]` for a pure FIR stage."""

    correction: float
    """Time correction (seconds) already applied to the recorded data to
    cancel this stage's own filter delay.

    Equivalent to FDSN StationXML's `Decimation/Correction` (SEED Blockette
    57 field 8). Real digitisers timestamp their output as if this stage
    had zero delay, by shifting the data earlier by this amount; evaluating
    `numerator`/`denominator` alone (e.g. via `scipy.signal.freqz`) instead
    reproduces the filter's own, uncorrected delay. `0.0` (the default,
    correct for a stage with no such correction, e.g. a symmetric FIR
    stage where the coefficients themselves carry no net delay) leaves the
    coefficient-derived transfer function unchanged."""


@runtime_checkable
class StagedResponse(Response, Protocol):
    """Protocol class to define a `Response` with digital decimation stages.

    Extends `Response` with the digital FIR/IIR stages of the instrument's
    full signal chain, in stage (signal) order.
    """

    stages: list[ResponseStage]
    """Digital decimation stages, in signal order (stage 1 = closest to the
    analog sensor)."""


@define(kw_only=True)
class MiniResponse:
    """Minimal implementation of the [`Response`][pysmo.Response] type.

    Examples:
        ```python
        >>> from pysmo import MiniResponse, Response
        >>> response = MiniResponse(
        ...     poles=[-0.037 + 0.037j, -0.037 - 0.037j],
        ...     zeros=[0j, 0j],
        ...     overall_sensitivity=3.4e9,
        ...     input_units="M/S",
        ... )
        >>> isinstance(response, Response)
        True
        >>>
        ```
    """

    poles: list[complex] = field(
        converter=convert_to_complex_list,
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Response poles.

    See [`Response.poles`][pysmo.Response.poles] for more details.
    """

    zeros: list[complex] = field(
        converter=convert_to_complex_list,
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Response zeros.

    See [`Response.zeros`][pysmo.Response.zeros] for more details.
    """

    overall_sensitivity: NonZeroNumber = field(
        converter=float,
        validator=validate_nonzero,
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Scale factor combined with `poles`/`zeros` to reconstruct `H(f)`.

    See [`Response.overall_sensitivity`][pysmo.Response.overall_sensitivity]
    for more details.
    """

    reference_sensitivity: NonZeroNumber | None = field(
        default=None,
        converter=_convert_optional_float,
        validator=validators.optional(validate_nonzero),
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Total system sensitivity at the reference frequency, `A0` excluded.

    See
    [`Response.reference_sensitivity`][pysmo.Response.reference_sensitivity]
    for more details.
    """

    input_units: str = field(
        validator=validators.instance_of(str),
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Physical units produced by removing this response.

    See [`Response.input_units`][pysmo.Response.input_units] for more details.
    """


@define(kw_only=True)
class MiniResponseStage:
    """Minimal implementation of the [`ResponseStage`][pysmo.ResponseStage] type.

    Examples:
        ```python
        >>> from pysmo import MiniResponseStage, ResponseStage
        >>> stage = MiniResponseStage(
        ...     input_sample_rate=40.0,
        ...     decimation_factor=1,
        ...     numerator=[0.5, 0.5],
        ... )
        >>> isinstance(stage, ResponseStage)
        True
        >>> stage.denominator
        [1.0]
        >>>
        ```
    """

    input_sample_rate: PositiveNumber = field(
        converter=float,
        validator=validators.gt(0),
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Sample rate this stage's filter coefficients operate at.

    See [`ResponseStage.input_sample_rate`][pysmo.ResponseStage.input_sample_rate]
    for more details.
    """

    decimation_factor: int = field(
        converter=_convert_strict_int,
        validator=validators.gt(0),
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Integer decimation factor applied by this stage.

    See [`ResponseStage.decimation_factor`][pysmo.ResponseStage.decimation_factor]
    for more details.
    """

    numerator: list[float] = field(
        converter=_convert_float_list,
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Feedforward ("b") filter coefficients.

    See [`ResponseStage.numerator`][pysmo.ResponseStage.numerator] for more details.
    """

    denominator: list[float] = field(
        factory=lambda: [1.0],
        converter=_convert_float_list,
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Feedback ("a") filter coefficients.

    See [`ResponseStage.denominator`][pysmo.ResponseStage.denominator] for more details.
    """

    correction: float = field(
        default=0.0,
        converter=float,
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Time correction (seconds) already applied to cancel this stage's own
    filter delay.

    See [`ResponseStage.correction`][pysmo.ResponseStage.correction] for
    more details.
    """


@define(kw_only=True)
class MiniStagedResponse(MiniResponse):
    """Minimal implementation of the [`StagedResponse`][pysmo.StagedResponse] type.

    Examples:
        ```python
        >>> from pysmo import MiniStagedResponse, StagedResponse, Response
        >>> response = MiniStagedResponse(
        ...     poles=[-0.037 + 0.037j, -0.037 - 0.037j],
        ...     zeros=[0j, 0j],
        ...     overall_sensitivity=3.4e9,
        ...     input_units="M/S",
        ... )
        >>> isinstance(response, StagedResponse)
        True
        >>> isinstance(response, Response)
        True
        >>>
        ```
    """

    stages: list[ResponseStage] = field(
        factory=list,
        on_setattr=setters.pipe(setters.convert, setters.validate),
    )
    """Digital decimation stages, in signal order.

    See [`StagedResponse.stages`][pysmo.StagedResponse.stages] for more details.
    """
