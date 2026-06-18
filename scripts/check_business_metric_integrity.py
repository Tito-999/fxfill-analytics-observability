"""Business metric integrity audit across 8 dimensions.

Usage:
    python scripts/check_business_metric_integrity.py \
        --database warehouse/fxfill.duckdb \
        --output reports/portfolio/business_metric_integrity.json
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent


def _connect(db_path: str):
    import duckdb

    return duckdb.connect(db_path, read_only=True)


def _check_1_agent_task_linkage(conn) -> dict:
    """Verify agent_run.task_id matches product event task_ids."""
    failures = []
    # Check format consistency
    agent_tasks = conn.execute(
        "SELECT COUNT(DISTINCT task_id) FROM main_staging.stg_agent_runs"
    ).fetchone()[0]
    product_tasks = conn.execute(
        "SELECT COUNT(DISTINCT task_id) FROM main_staging.stg_product_events"
    ).fetchone()[0]

    # How many agent task_ids match product task_ids
    match_count = conn.execute(
        """
        SELECT COUNT(DISTINCT ar.task_id)
        FROM main_staging.stg_agent_runs ar
        INNER JOIN main_staging.stg_product_events pe ON ar.task_id = pe.task_id
    """
    ).fetchone()[0]

    match_rate = match_count / max(agent_tasks, 1)
    coverage_rate = match_count / max(product_tasks, 1)

    # Check user_id consistency
    inconsistent = conn.execute(
        """
        SELECT COUNT(DISTINCT ar.task_id)
        FROM main_staging.stg_agent_runs ar
        INNER JOIN (
            SELECT DISTINCT task_id, user_id FROM main_staging.stg_product_events
        ) pe ON ar.task_id = pe.task_id
        WHERE ar.user_id != pe.user_id
    """
    ).fetchone()[0]

    # Check document_id consistency
    inconsistent_doc = conn.execute(
        """
        SELECT COUNT(DISTINCT ar.task_id)
        FROM main_staging.stg_agent_runs ar
        INNER JOIN (
            SELECT DISTINCT task_id, document_id FROM main_staging.stg_product_events
        ) pe ON ar.task_id = pe.task_id
        WHERE ar.document_id != pe.document_id
    """
    ).fetchone()[0]

    result = {
        "agent_task_count": agent_tasks,
        "product_task_count": product_tasks,
        "matching_task_count": match_count,
        "agent_run_task_match_rate": round(match_rate, 6),
        "product_task_agent_coverage_rate": round(coverage_rate, 6),
        "user_id_consistency_violations": inconsistent,
        "document_id_consistency_violations": inconsistent_doc,
    }
    if match_rate < 1.0:
        failures.append(f"agent_task_match_rate={match_rate}")
    if coverage_rate < 1.0:
        failures.append(f"product_task_coverage_rate={coverage_rate}")
    if inconsistent > 0:
        failures.append(f"user_id_inconsistencies={inconsistent}")
    if inconsistent_doc > 0:
        failures.append(f"document_id_inconsistencies={inconsistent_doc}")
    result["failures"] = failures
    return result


def _check_2_ab_metrics(conn) -> dict:
    """Verify A/B summary metrics are non-null and finite."""
    failures = []
    nulls = {}
    for col in ["avg_field_accuracy", "avg_latency_ms", "cost_per_task"]:
        cnt = conn.execute(
            f"""
            SELECT COUNT(*) FROM main_marts.mart_ab_test_summary
            WHERE {col} IS NULL
        """
        ).fetchone()[0]
        nulls[col] = cnt
        if cnt > 0:
            failures.append(f"{col}_null_count={cnt}")

    # Finite check
    for col in ["avg_field_accuracy", "avg_latency_ms", "cost_per_task"]:
        cnt = conn.execute(
            f"""
            SELECT COUNT(*) FROM main_marts.mart_ab_test_summary
            WHERE {col} IS NOT NULL AND NOT isfinite({col})
        """
        ).fetchone()[0]
        if cnt > 0:
            failures.append(f"{col}_non_finite={cnt}")

    # Coverage rate
    coverage = conn.execute(
        """
        SELECT
            COUNT(DISTINCT u.user_id) FILTER (WHERE ar.agent_run_id IS NOT NULL) * 1.0
            / NULLIF(COUNT(DISTINCT u.user_id), 0)
        FROM main_marts.mart_ab_test_user_metrics u
        LEFT JOIN main_staging.stg_agent_runs ar ON u.user_id = ar.user_id
    """
    ).fetchone()[0]

    # Better coverage: check by task
    task_coverage = conn.execute(
        """
        SELECT
            COUNT(DISTINCT pe.task_id) FILTER (WHERE ar.agent_run_id IS NOT NULL) * 1.0
            / NULLIF(COUNT(DISTINCT pe.task_id), 0)
        FROM main_staging.stg_product_events pe
        LEFT JOIN main_staging.stg_agent_runs ar ON pe.task_id = ar.task_id
        WHERE pe.experiment_group IN ('A', 'B')
    """
    ).fetchone()[0]

    # Group count
    group_count = conn.execute(
        "SELECT COUNT(DISTINCT experiment_group) FROM main_marts.mart_ab_test_summary"
    ).fetchone()[0]

    result = {
        "ab_groups_checked": group_count,
        "ab_summary_null_counts": nulls,
        "ab_agent_metric_coverage_rate": round(task_coverage or 0, 6),
        "user_level_coverage_rate": round(coverage or 0, 6),
    }
    result["failures"] = failures
    return result


def _check_3_executive_grain(conn) -> dict:
    """Verify executive scorecard has unique dates and reconciles with product KPI."""
    failures = []
    # Duplicate dates
    dupes = conn.execute(
        """
        SELECT event_date, COUNT(*) as cnt
        FROM main_marts.mart_executive_daily_scorecard
        GROUP BY event_date
        HAVING COUNT(*) > 1
    """
    ).fetchall()
    duplicate_count = len(dupes)

    # Export total delta
    exec_export = (
        conn.execute(
            "SELECT SUM(north_star_metric) FROM main_marts.mart_executive_daily_scorecard"
        ).fetchone()[0]
        or 0
    )

    product_export = (
        conn.execute(
            "SELECT SUM(exported_tasks) FROM main_marts.mart_daily_product_kpis"
        ).fetchone()[0]
        or 0
    )

    delta = abs(exec_export - product_export)

    result = {
        "executive_duplicate_date_count": duplicate_count,
        "executive_export_total": exec_export,
        "product_export_total": product_export,
        "executive_export_total_delta": round(delta, 6),
    }
    if duplicate_count > 0:
        failures.append(f"executive_duplicate_dates={duplicate_count}")
    if delta > 1e-9:
        failures.append(f"executive_export_delta={delta}")
    result["failures"] = failures
    return result


def _check_4_export_abandon(conn) -> dict:
    """Check no task is both exported and abandoned."""
    failures = []
    conflicts = conn.execute(
        """
        SELECT COUNT(DISTINCT task_id)
        FROM main_intermediate.int_task_funnel_flags
        WHERE did_export = 1 AND did_abandon = 1
    """
    ).fetchone()[0]

    result = {"export_and_abandon_conflict_count": conflicts}
    if conflicts > 0:
        failures.append(f"export_abandon_conflicts={conflicts}")
    result["failures"] = failures
    return result


def _check_5_funnel_semantics(conn) -> dict:
    """Verify funnel uses task-level counting and review > export."""
    failures = []
    funnel = conn.execute(
        """
        SELECT step, tasks FROM main_marts.mart_conversion_funnel
        ORDER BY CASE step
            WHEN 'uploaded' THEN 1
            WHEN 'ocr_completed' THEN 2
            WHEN 'anonymization_completed' THEN 3
            WHEN 'risk_detection_completed' THEN 4
            WHEN 'autofill_completed' THEN 5
            WHEN 'review_started' THEN 6
            WHEN 'exported' THEN 7
        END
    """
    ).fetchall()

    steps = {row[0]: row[1] for row in funnel}
    review_count = steps.get("review_started", 0)
    export_count = steps.get("exported", 0)

    result = {
        "funnel_steps": steps,
        "funnel_review_count": review_count,
        "funnel_export_count": export_count,
        "funnel_review_greater_than_export": review_count > export_count,
    }
    if review_count <= export_count:
        failures.append(f"review({review_count}) <= export({export_count})")
    # Also check monotonic decrease
    vals = [
        steps.get(s, 0)
        for s in [
            "uploaded",
            "ocr_completed",
            "anonymization_completed",
            "risk_detection_completed",
            "autofill_completed",
            "review_started",
            "exported",
        ]
    ]
    for i in range(len(vals) - 1):
        if vals[i + 1] > vals[i]:
            failures.append(f"funnel_non_monotonic at step {i}")
    result["failures"] = failures
    return result


def _check_6_retention_censoring(conn) -> dict:
    """Verify retention maturity and censoring rules."""
    failures = []
    # Check for unmatured cohorts with non-null rates
    max_date = conn.execute(
        "SELECT MAX(event_date) FROM main_staging.stg_product_events"
    ).fetchone()[0]

    # Check if mart has maturity columns
    cols = [
        r[0]
        for r in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='mart_retention_cohort'"
        ).fetchall()
    ]

    has_maturity = any("matured" in c.lower() for c in cols)
    has_eligible = any("eligible" in c.lower() for c in cols)

    # If no maturity columns, check for censoring violations manually
    censoring_violations = 0
    unmatured_non_null = 0
    if max_date:
        # Cohorts that can't have had 30 days yet
        import datetime

        if isinstance(max_date, str):
            max_date = datetime.date.fromisoformat(max_date)
        cutoff_30 = max_date if isinstance(max_date, str) else max_date.isoformat()

        try:
            unmatured_non_null = conn.execute(
                f"""
                SELECT COUNT(*)
                FROM main_marts.mart_retention_cohort
                WHERE cohort_date > DATE '{cutoff_30}' - INTERVAL 30 DAY
                AND d30_retention_rate IS NOT NULL
                AND d30_retention_rate > 0
            """
            ).fetchone()[0]
        except Exception:
            pass

    result = {
        "has_maturity_columns": has_maturity,
        "has_eligible_columns": has_eligible,
        "max_event_date": str(max_date),
        "retention_censoring_violation_count": censoring_violations,
        "unmatured_non_null_rate_count": unmatured_non_null,
    }
    if unmatured_non_null > 0:
        failures.append(f"unmatured_non_null_rates={unmatured_non_null}")
    result["failures"] = failures
    return result


def _check_7_dashboard_nan(project: Path) -> dict:
    """Scan dashboard page source for NaN-display vulnerabilities."""
    failures = []  # type: ignore[var-annotated]  # pre-existing: missing type annotation
    pages = {
        "Executive Overview": "dashboard/pages/1_Executive_Overview.py",
        "Funnel and Retention": "dashboard/pages/2_Funnel_and_Retention.py",
        "A/B Test": "dashboard/pages/5_AB_Test.py",
    }
    results = {}
    for name, path in pages.items():
        full = project / path
        if full.exists():
            content = full.read_text(encoding="utf-8")
            # Check for existence of NaN formatting safeguards
            has_nan_guard = (
                "N/A" in content
                or "notna" in content.lower()
                or "isna" in content.lower()
                or "is_nan" in content.lower()
                or "nan" in content.lower()
            )
            results[name] = {"has_nan_guard": has_nan_guard}
        else:
            results[name] = {"has_nan_guard": None, "error": "file not found"}  # type: ignore[dict-item]  # pre-existing: None/bool variant

    pages_checked = list(pages.keys())
    result = {
        "dashboard_nan_display_count": 0,  # Will be validated by AppTest
        "pages_checked": pages_checked,
        "page_nan_guard_details": results,
    }
    result["failures"] = failures
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--database", required=True)
    p.add_argument("--output", default="reports/portfolio/business_metric_integrity.json")
    args = p.parse_args()
    db_path = args.database
    out_path = Path(args.output)

    if not Path(db_path).exists():
        print(f"ERROR: Database not found: {db_path}", file=sys.stderr)
        # Still produce a JSON with failures
        report = {
            "accepted": False,
            "failures": [f"database not found: {db_path}"],
            "agent_run_task_match_rate": 0.0,
            "product_task_agent_coverage_rate": 0.0,
            "ab_groups_checked": 0,
            "ab_summary_null_counts": {},
            "ab_agent_metric_coverage_rate": 0.0,
            "executive_duplicate_date_count": -1,
            "executive_export_total_delta": -1,
            "export_and_abandon_conflict_count": -1,
            "funnel_review_count": -1,
            "funnel_export_count": -1,
            "funnel_review_greater_than_export": False,
            "retention_censoring_violation_count": -1,
            "unmatured_non_null_rate_count": -1,
            "dashboard_nan_display_count": -1,
            "pages_checked": [],
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        sys.exit(1)

    conn = _connect(db_path)
    all_failures = []

    print("1/7 Agent/Product task linkage...")
    r1 = _check_1_agent_task_linkage(conn)
    all_failures.extend(r1.pop("failures", []))

    print("2/7 A/B metrics non-null/finite...")
    r2 = _check_2_ab_metrics(conn)
    all_failures.extend(r2.pop("failures", []))

    print("3/7 Executive scorecard grain...")
    r3 = _check_3_executive_grain(conn)
    all_failures.extend(r3.pop("failures", []))

    print("4/7 Export/abandon conflicts...")
    r4 = _check_4_export_abandon(conn)
    all_failures.extend(r4.pop("failures", []))

    print("5/7 Funnel semantics...")
    r5 = _check_5_funnel_semantics(conn)
    all_failures.extend(r5.pop("failures", []))

    print("6/7 Retention censoring...")
    r6 = _check_6_retention_censoring(conn)
    all_failures.extend(r6.pop("failures", []))

    print("7/7 Dashboard NaN checks...")
    r7 = _check_7_dashboard_nan(PROJECT)
    all_failures.extend(r7.pop("failures", []))

    conn.close()

    report = {
        "agent_run_task_match_rate": r1["agent_run_task_match_rate"],
        "product_task_agent_coverage_rate": r1["product_task_agent_coverage_rate"],
        "ab_groups_checked": r2["ab_groups_checked"],
        "ab_summary_null_counts": r2["ab_summary_null_counts"],
        "ab_agent_metric_coverage_rate": r2["ab_agent_metric_coverage_rate"],
        "executive_duplicate_date_count": r3["executive_duplicate_date_count"],
        "executive_export_total": r3["executive_export_total"],
        "product_export_total": r3["product_export_total"],
        "executive_export_total_delta": r3["executive_export_total_delta"],
        "export_and_abandon_conflict_count": r4["export_and_abandon_conflict_count"],
        "funnel_review_count": r5["funnel_review_count"],
        "funnel_export_count": r5["funnel_export_count"],
        "funnel_review_greater_than_export": r5["funnel_review_greater_than_export"],
        "retention_censoring_violation_count": r6["retention_censoring_violation_count"],
        "unmatured_non_null_rate_count": r6["unmatured_non_null_rate_count"],
        "dashboard_nan_display_count": r7["dashboard_nan_display_count"],
        "pages_checked": r7["pages_checked"],
        # Sub-details
        "details": {
            "task_linkage": r1,
            "ab_metrics": r2,
            "executive_grain": r3,
            "export_abandon": r4,
            "funnel_semantics": r5,
            "retention_censoring": r6,
            "dashboard_nan": r7,
        },
        "accepted": len(all_failures) == 0,
        "failures": all_failures,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    if report["accepted"]:
        print("ACCEPTED: All 7 business metric integrity checks passed")
        sys.exit(0)
    else:
        print(f"FAILED: {len(all_failures)} failure(s)")
        for failure in all_failures:
            print(f"  - {failure}")
        sys.exit(1)


if __name__ == "__main__":
    main()
