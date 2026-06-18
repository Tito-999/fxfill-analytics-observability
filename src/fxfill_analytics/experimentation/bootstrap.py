"""Deterministic user-level bootstrap for A/B metric comparison.

Resamples *users* (not events) with replacement within each group and
computes the bootstrap distribution of the group difference.
"""

from __future__ import annotations

import numpy as np


def bootstrap_diff(
    a_values: list[float],
    b_values: list[float],
    iterations: int = 5000,
    seed: int = 20260616,
    statistic: str = "mean",
) -> dict[str, float | None | int | str]:
    """Bootstrap the difference in a statistic between two groups.

    Parameters
    ----------
    a_values : list[float]
        Per-user values for group A.
    b_values : list[float]
        Per-user values for group B.
    iterations : int, default=5000
        Number of bootstrap replications.
    seed : int, default=20260616
        Random seed for reproducibility.
    statistic : str, default="mean"
        ``"mean"`` or ``"median"``.

    Returns
    -------
    dict
        ``estimate`` (bias-corrected), ``std_err``, ``ci_lower``,
        ``ci_upper``, ``observed_diff``, ``seed``, ``iterations``.
    """
    a = np.array(a_values, dtype=float)
    b = np.array(b_values, dtype=float)
    n_a, n_b = len(a), len(b)

    if n_a == 0 or n_b == 0:
        return {
            "estimate": None,
            "std_err": None,
            "ci_lower": None,
            "ci_upper": None,
            "observed_diff": None,
            "seed": seed,
            "iterations": iterations,
            "note": "One or both groups have no data.",
        }

    rng = np.random.default_rng(seed)

    stat_func = np.mean if statistic == "mean" else np.median

    # Observed difference (B - A)
    observed_diff = float(stat_func(b) - stat_func(a))  # type: ignore[operator]  # pre-existing: unknown function type

    # ── bootstrap distribution ───────────────────────────────────────
    boot_diffs = np.empty(iterations)
    for i in range(iterations):
        boot_a = a[rng.integers(0, n_a, size=n_a)]
        boot_b = b[rng.integers(0, n_b, size=n_b)]
        boot_diffs[i] = stat_func(boot_b) - stat_func(boot_a)  # type: ignore[operator]  # pre-existing: unknown function type

    bootstrap_mean = float(np.mean(boot_diffs))
    bias = bootstrap_mean - observed_diff
    estimate = observed_diff - bias  # bias-corrected

    std_err = float(np.std(boot_diffs, ddof=1))

    # Percentile confidence interval
    alpha = 0.05
    ci_lower = float(np.percentile(boot_diffs, 100 * alpha / 2))
    ci_upper = float(np.percentile(boot_diffs, 100 * (1.0 - alpha / 2)))

    return {
        "estimate": estimate,
        "std_err": std_err,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "observed_diff": observed_diff,
        "bootstrap_mean": bootstrap_mean,
        "seed": seed,
        "iterations": iterations,
    }
