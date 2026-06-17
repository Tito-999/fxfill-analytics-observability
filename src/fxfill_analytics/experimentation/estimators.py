"""Binary and continuous statistical estimators for A/B tests.

All calculations use ``scipy.stats`` and return dictionary results with
effect sizes, confidence intervals, and p-values.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats


def binary_effect(
    a_success: int,
    a_n: int,
    b_success: int,
    b_n: int,
) -> dict[str, float]:
    """Compare two proportions: risk difference, relative risk, odds ratio,
    and a two-sided z-test p-value.

    Parameters
    ----------
    a_success : int
        Number of successes in group A (control).
    a_n : int
        Total observations in group A.
    b_success : int
        Number of successes in group B (treatment).
    b_n : int
        Total observations in group B.

    Returns
    -------
    dict
        ``risk_difference``, ``relative_risk``, ``odds_ratio``,
        ``p_value_ztest``, ``ci_lower``, ``ci_upper``, ``a_rate``, ``b_rate``.
    """
    if a_n <= 0 or b_n <= 0:
        raise ValueError("Group sizes must be positive.")

    p_a = a_success / a_n
    p_b = b_success / b_n

    # ── effect sizes ─────────────────────────────────────────────────
    risk_difference = p_b - p_a
    relative_risk = p_b / p_a if p_a > 0 else float("inf")

    odds_a = a_success / max(a_n - a_success, 1)
    odds_b = b_success / max(b_n - b_success, 1)
    odds_ratio = odds_b / odds_a if odds_a > 0 else float("inf")

    # ── z-test for difference in proportions ─────────────────────────
    p_pool = (a_success + b_success) / (a_n + b_n)
    se = np.sqrt(p_pool * (1.0 - p_pool) * (1.0 / a_n + 1.0 / b_n))
    z_stat = risk_difference / se if se > 0 else 0.0
    p_value_ztest = 2.0 * (1.0 - stats.norm.cdf(abs(z_stat)))

    # ── confidence interval (normal approximation) ───────────────────
    se_diff = np.sqrt(p_a * (1.0 - p_a) / a_n + p_b * (1.0 - p_b) / b_n)
    z_crit = stats.norm.ppf(0.975)
    ci_lower = risk_difference - z_crit * se_diff
    ci_upper = risk_difference + z_crit * se_diff

    return {
        "risk_difference": float(risk_difference),
        "relative_risk": float(relative_risk),
        "odds_ratio": float(odds_ratio),
        "p_value_ztest": float(p_value_ztest),
        "ci_lower": float(ci_lower),
        "ci_upper": float(ci_upper),
        "a_rate": float(p_a),
        "b_rate": float(p_b),
    }


def continuous_effect(
    a_values: list[float],
    b_values: list[float],
) -> dict[str, float]:
    """Compare two continuous distributions with Welch's t-test.

    Parameters
    ----------
    a_values : list[float]
        Per-user metric values for group A (control).
    b_values : list[float]
        Per-user metric values for group B (treatment).

    Returns
    -------
    dict
        ``mean_diff``, ``welch_t_stat``, ``welch_p_value``,
        ``cohens_d``, ``ci_lower``, ``ci_upper``, ``a_mean``, ``b_mean``,
        ``a_std``, ``b_std``.
    """
    a = np.array(a_values, dtype=float)
    b = np.array(b_values, dtype=float)

    n_a, n_b = len(a), len(b)

    if n_a < 2 or n_b < 2:
        raise ValueError("Each group must have at least 2 observations.")

    mean_a = float(np.mean(a))
    mean_b = float(np.mean(b))
    std_a = float(np.std(a, ddof=1))
    std_b = float(np.std(b, ddof=1))

    mean_diff = mean_b - mean_a

    # ── Welch's t-test ───────────────────────────────────────────────
    t_stat, p_value = stats.ttest_ind(a, b, equal_var=False)

    # ── Cohen's d (pooled std with Welch's correction) ───────────────
    pooled_std = np.sqrt((std_a**2 + std_b**2) / 2.0)
    cohens_d = mean_diff / pooled_std if pooled_std > 0 else 0.0

    # ── confidence interval for the mean difference ──────────────────
    se_diff = np.sqrt(std_a**2 / n_a + std_b**2 / n_b)

    # Welch-Satterthwaite degrees of freedom
    num = (std_a**2 / n_a + std_b**2 / n_b) ** 2
    denom = (std_a**2 / n_a) ** 2 / (n_a - 1) + (std_b**2 / n_b) ** 2 / (n_b - 1)
    df = num / denom if denom > 0 else float(min(n_a, n_b) - 1)

    t_crit = stats.t.ppf(0.975, df=df)
    ci_lower = mean_diff - t_crit * se_diff
    ci_upper = mean_diff + t_crit * se_diff

    return {
        "mean_diff": float(mean_diff),
        "welch_t_stat": float(t_stat),
        "welch_p_value": float(p_value),
        "cohens_d": float(cohens_d),
        "ci_lower": float(ci_lower),
        "ci_upper": float(ci_upper),
        "a_mean": float(mean_a),
        "b_mean": float(mean_b),
        "a_std": float(std_a),
        "b_std": float(std_b),
    }
