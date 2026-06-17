"""Generate a structured A/B experiment analysis report.

Orchestrates all experimentation sub-modules and returns a complete
dictionary suitable for JSON serialization.
"""

from __future__ import annotations

from typing import Any

import duckdb
import numpy as np

from fxfill_analytics import settings
from fxfill_analytics.experimentation import (
    bootstrap,
    estimators,
    multiplicity,
)
from fxfill_analytics.experimentation import (
    config as cfg,
)
from fxfill_analytics.experimentation import (
    decision as decision_module,
)
from fxfill_analytics.experimentation import (
    guardrails as guard_module,
)
from fxfill_analytics.experimentation import (
    metrics as metrics_module,
)
from fxfill_analytics.experimentation import (
    srm as srm_module,
)

# ---------------------------------------------------------------------------
# Mapping from metric names in the YAML config to column keys in the
# per-user metrics dict returned by ``get_user_metrics``.
# ---------------------------------------------------------------------------
METRIC_COLUMN_MAP: dict[str, str] = {
    # Config name -> Actual column name in metrics_data
    "form_export_rate": "task_success_rate",
    "task_success_rate": "task_success_rate",
    "field_accuracy": "avg_field_accuracy",
    "avg_field_accuracy": "avg_field_accuracy",
    "avg_agent_latency_ms": "avg_agent_latency_ms",
    "avg_latency_ms": "avg_agent_latency_ms",
    "latency_ms": "avg_agent_latency_ms",
    "p95_latency_ms": "avg_agent_latency_ms",
    "total_cost_usd": "total_cost_usd",
    "cost_per_successful_task_usd": "total_cost_usd",
    # generic / derived
    "total_tasks": "total_tasks",
    "successful_tasks": "successful_tasks",
    "export_rate": "task_success_rate",
    "abandonment_rate": "successful_tasks",
    "error_rate": "avg_field_accuracy",
    "manual_edit_rate": "avg_field_edits",
    "avg_field_edits": "avg_field_edits",
    "avg_task_duration_s": "avg_task_duration_s",
}

# Metrics that are "lower is better" (default for guardrails).
_LOWER_IS_BETTER: set[str] = {
    "avg_agent_latency_ms",
    "avg_latency_ms",
    "p95_latency_ms",
    "latency_ms",
    "total_cost_usd",
    "cost_per_successful_task_usd",
    "cost_usd",
    "abandonment_rate",
    "error_rate",
    "agent_error_rate",
    "avg_field_edits",
    "avg_task_duration_s",
}


def generate_report(
    experiment_id: str,
    conn: duckdb.DuckDBPyConnection | None = None,
) -> dict[str, Any]:
    """Generate a full structured analysis report for *experiment_id*.

    Parameters
    ----------
    experiment_id : str
        Experiment identifier.
    conn : duckdb.DuckDBPyConnection, optional
        DuckDB connection.  Creates one from the configured path if omitted.

    Returns
    -------
    dict
        Complete report with sections: config, srm, user_metrics,
        primary_metric, secondary_metrics, guardrails,
        multiplicity_correction, decision.
    """
    should_close = False
    if conn is None:
        conn = duckdb.connect(str(settings.get_duckdb_path()))
        should_close = True

    try:
        # 1. Experiment configuration
        config: dict[str, Any] = cfg.load_experiment_config(experiment_id)
        # Resolve the database experiment ID from config; fall back to the
        # config key itself if no explicit mapping is present.
        db_experiment_id: str = config.get("experiment_id", experiment_id)
        analysis_cfg: dict[str, Any] = config.get("analysis", {})
        alpha: float = analysis_cfg.get("significance_level", 0.05)
        boot_iter: int = analysis_cfg.get("bootstrap_iterations", 10000)
        boot_seed: int = settings.get_data_seed()

        # 2. SRM test
        srm_result: dict[str, Any] = srm_module.srm_test(
            db_experiment_id,
            conn=conn,
            config=config,
        )

        # 3. User-level metrics (contaminated users excluded)
        user_metrics: dict[str, Any] = metrics_module.get_user_metrics(
            db_experiment_id,
            conn=conn,
        )
        groups: list[str] = user_metrics.get("groups", [])
        metrics_data: dict[str, dict[str, list[float]]] = user_metrics.get("metrics", {})

        primary_configs: list[dict[str, Any]] = config.get("metrics", {}).get("primary", [])
        secondary_configs: list[dict[str, Any]] = config.get("metrics", {}).get("secondary", [])
        guardrail_configs: list[dict[str, Any]] = config.get("guardrails", [])

        # 4. Primary metric analysis
        primary_results = _analyze_named_metrics(
            primary_configs,
            metrics_data,
            groups,
            alpha,
            boot_iter,
            boot_seed,
        )
        primary_result: dict[str, Any] | None = primary_results[0] if primary_results else None

        # 5. Secondary metric analysis
        secondary_results = _analyze_named_metrics(
            secondary_configs,
            metrics_data,
            groups,
            alpha,
            boot_iter,
            boot_seed,
        )

        # 6. Benjamini-Hochberg correction on secondary p-values
        sec_pvals = [
            r.get("p_value") or r.get("welch_p_value", 1.0)
            for r in secondary_results
            if "p_value" in r or "welch_p_value" in r
        ]
        if sec_pvals:
            corrected = multiplicity.bh_correction(sec_pvals, alpha=alpha)
            for corr, res in zip(corrected, secondary_results, strict=False):
                if "p_value" in res or "welch_p_value" in res:
                    res["adjusted_p"] = corr["adjusted_p"]
                    res["bh_rejected"] = corr["rejected"]

        # 7. Guardrail analysis
        guardrail_results = _analyze_guardrails(
            guardrail_configs,
            metrics_data,
            groups,
        )

        # 8. Decision
        decision_result: dict[str, Any] = decision_module.make_decision(
            primary_result=primary_result,
            guardrail_results=guardrail_results,
            srm_passed=srm_result.get("passed", True),
            data_validation_passed=True,
            experiment_id=experiment_id,
        )

        # 9. Assemble report
        report: dict[str, Any] = {
            "experiment_id": experiment_id,
            "experiment_name": config.get("name", experiment_id),
            "config": {
                "significance_level": alpha,
                "bootstrap_iterations": boot_iter,
                "bootstrap_seed": boot_seed,
                "srm_alpha": srm_result.get("srm_alpha", 0.05),
            },
            "srm": srm_result,
            "user_metrics": {
                "groups": groups,
                "n_users": user_metrics.get("n_users", {}),
                "contaminated_excluded": user_metrics.get("contaminated_excluded", 0),
                "summary_stats": _compute_summary_stats(metrics_data, groups),
            },
            "primary_metric": primary_result,
            "secondary_metrics": secondary_results,
            "guardrails": guardrail_results,
            "multiplicity_correction": {
                "method": "Benjamini-Hochberg",
                "alpha": alpha,
                "n_tests": len(sec_pvals),
            },
            "decision": decision_result,
        }

        return report

    finally:
        if should_close:
            conn.close()


# ======================================================================
# Internal helpers
# ======================================================================


def _analyze_named_metrics(
    metric_configs: list[dict[str, Any]],
    metrics_data: dict[str, dict[str, list[float]]],
    groups: list[str],
    alpha: float,
    boot_iter: int,
    boot_seed: int,
) -> list[dict[str, Any]]:
    """Run continuous-effect estimation + bootstrap for each named metric."""
    if len(groups) < 2:
        return [
            {
                "metric_name": mc.get("name", "unknown"),
                "status": "insufficient_groups",
                "note": f"Need at least 2 groups, found {len(groups)}.",
            }
            for mc in metric_configs
        ]

    a_group, b_group = groups[0], groups[-1]
    results: list[dict[str, Any]] = []

    for mc in metric_configs:
        name: str = mc.get("name", "unknown")
        direction: str = mc.get("direction", "higher_is_better")
        col: str = METRIC_COLUMN_MAP.get(name, name)

        a_vals = metrics_data.get(a_group, {}).get(col, [])
        b_vals = metrics_data.get(b_group, {}).get(col, [])

        if not a_vals or not b_vals:
            results.append(
                {
                    "metric_name": name,
                    "direction": direction,
                    "status": "no_data",
                    "note": f"Metric column {col!r} not available for both groups.",
                }
            )
            continue

        # Continuous Welch t-test
        try:
            cont = estimators.continuous_effect(a_vals, b_vals)
        except ValueError:
            results.append(
                {
                    "metric_name": name,
                    "direction": direction,
                    "status": "insufficient_data",
                    "note": "One or both groups have fewer than 2 observations.",
                }
            )
            continue

        # Bootstrap
        boot = bootstrap.bootstrap_diff(
            a_vals,
            b_vals,
            iterations=boot_iter,
            seed=boot_seed,
        )

        p_val = cont["welch_p_value"]
        is_nan = bool(np.isnan(p_val)) if p_val is not None else True
        is_sig = bool(not is_nan and p_val < alpha)

        result: dict[str, Any] = {
            "metric_name": name,
            "direction": direction,
            "status": "constant_data" if is_nan else "ok",
            "a_mean": cont["a_mean"],
            "b_mean": cont["b_mean"],
            "mean_diff": cont["mean_diff"],
            "p_value": cont["welch_p_value"],
            "ci_lower": cont["ci_lower"],
            "ci_upper": cont["ci_upper"],
            "cohens_d": cont["cohens_d"],
            "is_significant": is_sig,
            "bootstrap": boot,
        }
        if is_nan:
            result["note"] = "Both groups have constant values — effect cannot be estimated."
        results.append(result)

    return results


def _analyze_guardrails(
    guardrail_configs: list[dict[str, Any]],
    metrics_data: dict[str, dict[str, list[float]]],
    groups: list[str],
) -> list[dict[str, Any]]:
    """Run non-inferiority tests for each guardrail."""
    if len(groups) < 2:
        return [
            {
                "metric_name": gc.get("name", "unknown"),
                "status": "insufficient_groups",
            }
            for gc in guardrail_configs
        ]

    a_group, b_group = groups[0], groups[-1]
    results: list[dict[str, Any]] = []

    for gc in guardrail_configs:
        name: str = gc.get("name", "unknown")
        margin: float = gc.get("threshold_relative", 1.10)
        col: str = METRIC_COLUMN_MAP.get(name, name)
        higher_is_better: bool = name not in _LOWER_IS_BETTER

        a_vals = metrics_data.get(a_group, {}).get(col, [])
        b_vals = metrics_data.get(b_group, {}).get(col, [])

        if not a_vals or not b_vals:
            results.append(
                {
                    "metric_name": name,
                    "status": "no_data",
                    "note": f"Metric column {col!r} not available for both groups.",
                }
            )
            continue

        gr = guard_module.test_guardrail(
            a_vals,
            b_vals,
            margin=margin,
            higher_is_better=higher_is_better,
        )
        gr["metric_name"] = name
        gr["higher_is_better"] = higher_is_better
        gr["status"] = "ok"
        results.append(gr)

    return results


def _compute_summary_stats(
    metrics_data: dict[str, dict[str, list[float]]],
    groups: list[str],
) -> dict[str, dict[str, dict[str, float]]]:
    """Compute mean, std, quartiles, min, max per group per metric."""
    stats: dict[str, dict[str, dict[str, float]]] = {}
    for group in groups:
        group_stats: dict[str, dict[str, float]] = {}
        for metric_name, values in metrics_data.get(group, {}).items():
            arr = np.array(values, dtype=float)
            group_stats[metric_name] = {
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr, ddof=1)),
                "p25": float(np.percentile(arr, 25)),
                "p50": float(np.percentile(arr, 50)),
                "p75": float(np.percentile(arr, 75)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "n": int(len(arr)),
            }
        stats[group] = group_stats
    return stats
