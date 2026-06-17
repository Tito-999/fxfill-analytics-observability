"""Sample Ratio Mismatch (SRM) test via chi-square goodness-of-fit.

Queries user counts per experiment group from
``main_intermediate.int_experiment_clean_assignments`` and compares them
against the expected allocation using a chi-square test.
"""

from __future__ import annotations

from typing import Any

import duckdb
import numpy as np
from scipy import stats

from fxfill_analytics import settings


def srm_test(
    experiment_id: str,
    conn: duckdb.DuckDBPyConnection | None = None,
    expected_allocation: list[float] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Perform a Sample Ratio Mismatch test.

    Parameters
    ----------
    experiment_id : str
        Database experiment identifier.
    conn : duckdb.DuckDBPyConnection, optional
        DuckDB connection.  Creates one from the configured path if omitted.
    expected_allocation : list[float], optional
        Expected traffic-split proportions.  Defaults to the config value
        (usually ``[0.5, 0.5]``).
    config : dict, optional
        Pre-loaded experiment config.  If provided, ``expected_allocation``
        and ``srm_alpha`` are read from this dict instead of looking up by
        *experiment_id*.

    Returns
    -------
    dict
        ``chi2_stat``, ``p_value``, ``observed`` (``{group: count}``),
        ``expected`` (``{group: count}``), ``passed`` (``p_value >= alpha``),
        ``n_total``, ``srm_alpha``.
    """
    if conn is None:
        conn = duckdb.connect(str(settings.get_duckdb_path()))

    # ── resolve expected allocation ──────────────────────────────────
    if expected_allocation is None:
        if config is not None:
            expected_allocation = config.get("design", {}).get("traffic_split", [0.5, 0.5])
        else:
            expected_allocation = [0.5, 0.5]

    # ── query observed user counts ───────────────────────────────────
    result = conn.execute(
        """
        SELECT
            experiment_group,
            COUNT(DISTINCT user_id) AS user_count
        FROM main_intermediate.int_experiment_clean_assignments
        WHERE experiment_id = ?
        GROUP BY experiment_group
        ORDER BY experiment_group
        """,
        [experiment_id],
    ).fetchall()

    if not result:
        return {
            "chi2_stat": None,
            "p_value": None,
            "observed": {},
            "expected": {},
            "passed": True,
            "n_total": 0,
            "note": "No assignments found for experiment.",
        }

    groups = [row[0] for row in result]
    observed_counts = np.array([row[1] for row in result], dtype=float)
    n_total = observed_counts.sum().astype(int)

    # ── align expected proportions with observed groups ──────────────
    expected_props = np.array(expected_allocation, dtype=float)
    expected_props = expected_props / expected_props.sum()

    n_groups_obs = len(observed_counts)
    n_groups_exp = len(expected_props)

    if n_groups_obs > n_groups_exp:
        # Pad missing groups with equal share of remaining probability
        remaining = 1.0 - expected_props.sum()
        extra = remaining / (n_groups_obs - n_groups_exp)
        expected_props = np.append(expected_props, [extra] * (n_groups_obs - n_groups_exp))
    elif n_groups_obs < n_groups_exp:
        expected_props = expected_props[:n_groups_obs]
        expected_props = expected_props / expected_props.sum()

    expected_counts = expected_props * n_total

    # ── chi-square goodness-of-fit ───────────────────────────────────
    chi2_stat, p_value = stats.chisquare(f_obs=observed_counts, f_exp=expected_counts)

    # ── threshold ────────────────────────────────────────────────────
    if config is not None:
        srm_alpha = config.get("analysis", {}).get("srm_significance_level", 0.05)
    else:
        srm_alpha = 0.05

    passed = bool(float(p_value) >= srm_alpha)

    return {
        "chi2_stat": float(chi2_stat),
        "p_value": float(p_value),
        "observed": dict(zip(groups, map(int, observed_counts))),
        "expected": dict(zip(groups, map(float, expected_counts))),
        "passed": passed,
        "n_total": int(n_total),
        "srm_alpha": srm_alpha,
    }


