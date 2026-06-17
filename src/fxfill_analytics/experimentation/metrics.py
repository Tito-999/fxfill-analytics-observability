"""Retrieve per-user experiment metrics, excluding contaminated users.

Queries ``mart_ab_test_user_metrics`` joined with
``int_experiment_clean_assignments`` and filters out any user listed in
``int_experiment_contaminated_users``.
"""

from __future__ import annotations

from typing import Any

import duckdb

from fxfill_analytics import settings


def get_user_metrics(
    experiment_id: str,
    conn: duckdb.DuckDBPyConnection | None = None,
) -> dict[str, Any]:
    """Return per-user metric values split by experiment group.

    Parameters
    ----------
    experiment_id : str
        Experiment identifier.
    conn : duckdb.DuckDBPyConnection, optional
        DuckDB connection.  Creates one from the configured path if omitted.

    Returns
    -------
    dict
        ``groups`` — list of group labels (sorted).
        ``metrics`` — ``{group: {metric_name: [values]}}``.
        ``n_users`` — ``{group: count}``.
        ``contaminated_excluded`` — number of users dropped.
        ``experiment_id``.
    """
    if conn is None:
        conn = duckdb.connect(str(settings.get_duckdb_path()))

    # ── contaminated users ───────────────────────────────────────────
    contaminated_df = conn.execute(
        """
        SELECT DISTINCT user_id
        FROM main_intermediate.int_experiment_contaminated_users
        """,
    ).df()

    contaminated_set: set[str] = (
        set(contaminated_df["user_id"].tolist()) if not contaminated_df.empty else set()
    )
    n_contaminated = len(contaminated_set)

    # ── clean assignments + user metrics ─────────────────────────────
    df = conn.execute(
        """
        SELECT
            a.user_id,
            a.experiment_group,
            m.total_tasks,
            m.successful_tasks,
            m.task_success_rate,
            m.avg_field_accuracy,
            m.avg_agent_latency_ms,
            m.total_cost_usd,
            m.avg_field_edits,
            m.avg_task_duration_s
        FROM main_intermediate.int_experiment_clean_assignments a
        LEFT JOIN main_marts.mart_ab_test_user_metrics m
            ON a.user_id = m.user_id
        WHERE a.experiment_id = ?
          AND (a.is_contaminated IS NULL OR a.is_contaminated = FALSE)
        ORDER BY a.user_id
        """,
        [experiment_id],
    ).df()

    if df.empty:
        return {
            "groups": [],
            "metrics": {},
            "n_users": {},
            "contaminated_excluded": n_contaminated,
            "experiment_id": experiment_id,
        }

    before = len(df)
    df = df[~df["user_id"].isin(contaminated_set)]
    contaminated_excluded = before - len(df)

    # ── split by group ───────────────────────────────────────────────
    groups = sorted(df["experiment_group"].unique())

    metrics_dict: dict[str, dict[str, list[float]]] = {}
    n_users: dict[str, int] = {}

    for group in groups:
        gdf = df[df["experiment_group"] == group]
        n_users[group] = len(gdf)
        metrics_dict[group] = {
            "total_tasks": gdf["total_tasks"].fillna(0).tolist(),
            "successful_tasks": gdf["successful_tasks"].fillna(0).tolist(),
            "task_success_rate": gdf["task_success_rate"].fillna(0.0).tolist(),
            "avg_field_accuracy": gdf["avg_field_accuracy"].fillna(0.0).tolist(),
            "avg_agent_latency_ms": gdf["avg_agent_latency_ms"].fillna(0.0).tolist(),
            "total_cost_usd": gdf["total_cost_usd"].fillna(0.0).tolist(),
            "avg_field_edits": gdf["avg_field_edits"].fillna(0.0).tolist(),
            "avg_task_duration_s": gdf["avg_task_duration_s"].fillna(0.0).tolist(),
        }

    return {
        "groups": groups,
        "metrics": metrics_dict,
        "n_users": n_users,
        "contaminated_excluded": contaminated_excluded + (n_contaminated - (before - len(df))),
        "experiment_id": experiment_id,
    }
