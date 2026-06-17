"""Benjamini-Hochberg False Discovery Rate correction for multiple testing.
"""

from __future__ import annotations

from typing import Any


def bh_correction(
    p_values: list[float],
    alpha: float = 0.05,
) -> list[dict[str, Any]]:
    """Apply the Benjamini-Hochberg FDR procedure.

    Parameters
    ----------
    p_values : list[float]
        Raw p-values from multiple hypothesis tests.
    alpha : float, default=0.05
        Desired false discovery rate.

    Returns
    -------
    list[dict]
        Each entry is ``{"raw_p": float, "adjusted_p": float, "rejected": bool}``,
        sorted by adjusted p-value ascending.
    """
    n = len(p_values)
    if n == 0:
        return []

    # Sort p-values, keeping track of original indices
    indexed = list(enumerate(p_values))
    indexed_sorted = sorted(indexed, key=lambda x: x[1])

    # Raw BH-adjusted values (sorted order)
    adjusted_raw: list[float] = []
    for rank, (_, p) in enumerate(indexed_sorted):
        adjusted = p * n / (rank + 1)
        adjusted_raw.append(min(adjusted, 1.0))

    # Enforce monotonicity: adjusted_(i) <= adjusted_(i+1)
    for i in range(n - 2, -1, -1):
        adjusted_raw[i] = min(adjusted_raw[i], adjusted_raw[i + 1])

    # Determine the largest rank where adjusted_p <= alpha
    max_rejected = -1
    for i in range(n):
        if adjusted_raw[i] <= alpha:
            max_rejected = i

    # Map back to original order
    adjusted_original: list[float] = [0.0] * n
    rejected_original: list[bool] = [False] * n
    for i, (orig_idx, _) in enumerate(indexed_sorted):
        adjusted_original[orig_idx] = adjusted_raw[i]
        rejected_original[orig_idx] = i <= max_rejected

    # Build final result sorted by adjusted p-value
    result = sorted(
        [
            {
                "raw_p": float(p_values[i]),
                "adjusted_p": adjusted_original[i],
                "rejected": rejected_original[i],
            }
            for i in range(n)
        ],
        key=lambda x: x["adjusted_p"],
    )

    return result
