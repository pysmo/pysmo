"""Helpers shared by the stack and matrix image plots."""

from .._iccs import ICCS


def _make_mask(iccs: ICCS, all_seismograms: bool) -> list[bool]:
    """Return a list of booleans for selecting the data to use in the plots.

    Args:
        iccs: Instance of the ICCS class.
        all_seismograms: If `True`, create mask for all seismograms instead of selected
            ones only (effectively returns a list of True for all seismograms).

    Returns:
        List of booleans for selecting the data to use in the plots.
    """

    if all_seismograms:
        return [True] * len(iccs.seismograms)

    return [s.select for s in iccs.seismograms]


def _variant_suffix(apply: bool, causal: bool) -> str:
    """Return a label suffix identifying the causal/zero-phase filter variant.

    Only shown when `apply` is `True`; when it's `False`, causal and
    zero-phase preparation are identical, so labelling one as "(causal)"
    would be misleading.

    Takes `apply` explicitly rather than reading `ICCS.bandpass_apply`
    directly: `update_bandpass`'s live preview only writes
    `iccs.bandpass_apply` on a cache miss (see `_update_matrix`/
    `_update_stack`), so it can lag behind the widget's actual current
    state on a cache hit, so callers there must pass the freshly-read
    checkbox state instead of the (possibly stale) `iccs` attribute.
    """
    if not apply:
        return ""
    return " (causal)" if causal else " (zero-phase)"
