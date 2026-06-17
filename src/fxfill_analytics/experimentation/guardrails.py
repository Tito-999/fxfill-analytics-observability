"""Non-inferiority testing for experiment guardrail metrics.

Each guardrail is tested against a relative margin: the treatment mean must
not degrade beyond ``margin * control_mean`` (for lower-is-better metrics)
or fall below ``control_mean / margin`` (for higher-is-better metrics).
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats


def test_guardrail(
    a_values: list[float],
    b_values: list[float],
    margin: float,
    higher_is_better: bool = False,
) -> dict[str, Any]:
    """Test whether a guardrail metric's change stays within an acceptable
    relative margin.

    Parameters
    ----------
    a_values : list[float]
        Per-user values for group A (control).
    b_values : list[float]
        Per-user values for group B (treatment).
    margin : float
        Acceptable relative multiplier.  E.g. ``1.15`` means the treatment
        can be at most 15 % worse than the control.
    higher_is_better : bool, default=False
        *True* — a higher value is better (e.g. accuracy).
        *False* — a lower value is better (e.g. latency, cost).

    Returns
    -------
    dict
        ``diff``, ``diff_pct``, ``ci_lower``, ``ci_upper``, ``margin``,
        ``non_inferiority_passed``, ``a_mean``, ``b_mean``.
    """
    a = np.array(a_values, dtype=float)
    b = np.array(b_values, dtype=float)
    n_a, n_b = len(a), len(b)

    if n_a == 0 or n_b == 0:
        return {
            "diff": None,
            "diff_pct": None,
            "ci_lower": None,
            "ci_upper": None,
            "margin": margin,
            "non_inferiority_passed": True,
            "a_mean": float(np.mean(a)) if n_a else None,
            "b_mean": float(np.mean(b)) if n_b else None,
            "note": "One or both groups have no data.",
        }

    mean_a = float(np.mean(a))
    mean_b = float(np.mean(b))
    std_a = float(np.std(a, ddof=1))
    std_b = float(np.std(b, ddof=1))

    diff = mean_b - mean_a
    diff_pct = diff / mean_a * 100.0 if mean_a != 0.0 else 0.0

    # ── standard error & Welch df ────────────────────────────────────
    se_diff = np.sqrt(std_a**2 / n_a + std_b**2 / n_b)

    # Degenerate case: both groups are constant (all values identical).
    # No variability means no evidence of degradation — guardrail passes.
    if se_diff == 0.0:
        return {
            "diff": float(diff),
            "diff_pct": float(diff_pct),
            "ci_lower": float(diff),
            "ci_upper": float(diff),
            "margin": margin,
            "non_inferiority_passed": True,
            "a_mean": float(mean_a),
            "b_mean": float(mean_b),
            "note": "Zero variance in both groups — guardrail passes by default.",
        }

    num = (std_a**2 / n_a + std_b**2 / n_b) ** 2
    denom = (std_a**2 / n_a) ** 2 / (n_a - 1) + (std_b**2 / n_b) ** 2 / (n_b - 1)
    df = num / denom if denom > 0 else float(min(n_a, n_b) - 1)

    t_crit = stats.t.ppf(0.95, df=df)  # one-sided 95 % CI

    if not higher_is_better:
        # Lower is better (latency, cost, error rate).
        # Acceptable degradation = (margin - 1) * mean_a
        # Non-inferiority holds if the one-sided upper CI of diff < degradation.
        acceptable_degradation = (margin - 1.0) * mean_a
        ci_upper = diff + t_crit * se_diff
        ci_lower = diff - t_crit * se_diff
        passed = bool(ci_upper < acceptable_degradation)
    else:
        # Higher is better (accuracy, success rate).
        # Acceptable lower bound = - (1 - 1/margin) * mean_a
        acceptable_degradation = (1.0 / margin - 1.0) * mean_a
        ci_lower = diff - t_crit * se_diff
        ci_upper = diff + t_crit * se_diff
        passed = bool(ci_lower > acceptable_degradation)

    return {
        "diff": float(diff),
        "diff_pct": float(diff_pct),
        "ci_lower": float(ci_lower),
        "ci_upper": float(ci_upper),
        "margin": margin,
        "non_inferiority_passed": passed,
        "a_mean": float(mean_a),
        "b_mean": float(mean_b),
    }
