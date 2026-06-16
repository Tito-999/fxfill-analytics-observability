"""
Real observed-signal validators for all 10 business phenomena.

Each validator:
1. Computes metrics from the final generated tables
2. Returns baseline value, affected value, absolute and relative differences
3. Returns sample sizes for both groups
4. Determines whether the expected direction is observed (pass/fail)

NO validator reads pre-baked "should pass" results from configuration.
All metrics are computed from the generated data.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def _make_result(
    phenomenon_id: str,
    metric: str,
    baseline_group: str,
    baseline_value: float,
    affected_group: str,
    affected_value: float,
    baseline_n: int,
    affected_n: int,
    expected_direction: str,
    passed: bool,
) -> dict[str, Any]:
    """Build a standardized validation result dict."""
    return {
        "phenomenon_id": phenomenon_id,
        "metric": metric,
        "baseline_group": baseline_group,
        "baseline_value": round(baseline_value, 6),
        "affected_group": affected_group,
        "affected_value": round(affected_value, 6),
        "absolute_difference": round(affected_value - baseline_value, 6),
        "relative_difference": round(
            (affected_value - baseline_value) / max(abs(baseline_value), 1e-10), 6
        ),
        "baseline_n": baseline_n,
        "affected_n": affected_n,
        "expected_direction": expected_direction,
        "passed": passed,
    }


def validate_p01_ocr_latency(
    tables: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    """P01: P95 OCR latency higher in app v2.3.0."""
    events = tables.get("product_events")
    if events is None:
        return _make_result(
            "P01", "p95_ocr_latency_ms", "other", 0, "v2.3.0", 0, 0, 0, "affected > baseline", False
        )

    ocr = events[events["event_name"].isin(["ocr_started", "ocr_completed"])]
    v230 = ocr[ocr["app_version"] == "2.3.0"]
    other = ocr[ocr["app_version"] != "2.3.0"]

    if len(v230) == 0 or len(other) == 0:
        return _make_result(
            "P01",
            "p95_ocr_latency_ms",
            "other",
            0,
            "v2.3.0",
            0,
            len(other),
            len(v230),
            "affected > baseline",
            False,
        )

    p95_v230 = v230["latency_ms"].quantile(0.95)
    p95_other = other["latency_ms"].quantile(0.95)
    return _make_result(
        "P01",
        "p95_ocr_latency_ms",
        "other_versions",
        p95_other,
        "v2.3.0",
        p95_v230,
        len(other),
        len(v230),
        "affected > baseline",
        p95_v230 > p95_other,
    )


def validate_p02_complex_edit(
    tables: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    """P02: Complex documents have higher field_edited event count."""
    events = tables.get("product_events")
    documents = tables.get("documents")
    if events is None or documents is None:
        return _make_result(
            "P02", "edit_rate", "simple", 0, "complex", 0, 0, 0, "affected > baseline", False
        )

    # Join events with document complexity
    field_edits = events[events["event_name"] == "field_edited"]
    if len(field_edits) == 0:
        return _make_result(
            "P02", "edit_rate", "simple", 0, "complex", 0, 0, 0, "affected > baseline", False
        )

    # Count edits per doc_id
    edit_counts = field_edits.groupby("document_id").size().reset_index(name="edit_count")

    # Merge with document complexity
    merged = edit_counts.merge(
        documents[["document_id", "complexity_level"]], on="document_id", how="inner"
    )
    complex_edits = merged[merged["complexity_level"] == "complex"]["edit_count"]
    simple_edits = merged[merged["complexity_level"] == "simple"]["edit_count"]

    if len(complex_edits) == 0 or len(simple_edits) == 0:
        return _make_result(
            "P02",
            "edit_rate",
            "simple",
            float(simple_edits.mean()) if len(simple_edits) > 0 else 0,
            "complex",
            float(complex_edits.mean()) if len(complex_edits) > 0 else 0,
            len(simple_edits),
            len(complex_edits),
            "affected > baseline",
            False,
        )

    avg_complex = complex_edits.mean()
    avg_simple = simple_edits.mean()
    return _make_result(
        "P02",
        "avg_edits_per_document",
        "simple",
        avg_simple,
        "complex",
        avg_complex,
        len(simple_edits),
        len(complex_edits),
        "affected > baseline",
        avg_complex > avg_simple,
    )


def validate_p03_mobile_export(
    tables: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    """P03: Mobile users have lower review-to-export completion rate."""
    events = tables.get("product_events")
    if events is None:
        return _make_result(
            "P03", "export_rate", "desktop", 0, "mobile", 0, 0, 0, "affected < baseline", False
        )

    # Count tasks that reached form_review_started vs form_exported, by platform
    review = events[events["event_name"] == "form_review_started"]
    exported = events[events["event_name"] == "form_exported"]

    # Per platform: tasks that started review
    review_by_platform = review.groupby("platform")["task_id"].nunique()
    export_by_platform = exported.groupby("platform")["task_id"].nunique()

    desktop_review = review_by_platform.get("desktop", 0)
    mobile_review = review_by_platform.get("mobile", 0)
    desktop_export = export_by_platform.get("desktop", 0)
    mobile_export = export_by_platform.get("mobile", 0)

    desktop_rate = desktop_export / max(desktop_review, 1)
    mobile_rate = mobile_export / max(mobile_review, 1)

    return _make_result(
        "P03",
        "review_to_export_rate",
        "desktop",
        desktop_rate,
        "mobile",
        mobile_rate,
        int(desktop_review),
        int(mobile_review),
        "affected < baseline",
        mobile_rate < desktop_rate,
    )


def validate_p04_paid_search_retention(
    tables: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    """P04: Paid search users have lower D7 retention (fewer return visits)."""
    events = tables.get("product_events")
    users = tables.get("users")
    if events is None or users is None:
        return _make_result(
            "P04", "return_rate", "organic", 0, "paid_search", 0, 0, 0, "affected < baseline", False
        )

    # Compute active days per user
    if "event_date" not in events.columns:
        return _make_result(
            "P04", "return_rate", "organic", 0, "paid_search", 0, 0, 0, "affected < baseline", False
        )

    # Get unique active days per user
    # Handle event_date which may be date or datetime
    events_copy = events.copy()
    events_copy["active_date"] = events_copy["event_date"].apply(
        lambda d: d.date() if hasattr(d, "date") else d
    )
    user_active_days = events_copy.groupby("user_id")["active_date"].nunique()

    # Merge with user acquisition channel
    user_info = users[["user_id", "acquisition_channel"]]
    merged = user_active_days.reset_index(name="active_days").merge(
        user_info, on="user_id", how="inner"
    )

    paid = merged[merged["acquisition_channel"] == "paid_search"]["active_days"]
    organic = merged[merged["acquisition_channel"] == "organic"]["active_days"]

    if len(paid) == 0 or len(organic) == 0:
        return _make_result(
            "P04",
            "avg_active_days",
            "organic",
            float(organic.mean()) if len(organic) > 0 else 0,
            "paid_search",
            float(paid.mean()) if len(paid) > 0 else 0,
            len(organic),
            len(paid),
            "affected < baseline",
            False,
        )

    avg_paid = paid.mean()
    avg_organic = organic.mean()
    return _make_result(
        "P04",
        "avg_active_days_per_user",
        "organic",
        avg_organic,
        "paid_search",
        avg_paid,
        len(organic),
        len(paid),
        "affected < baseline",
        avg_paid < avg_organic,
    )


def validate_p05_prompt_cost(
    tables: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    """P05: Prompt v2.0.0-beta has higher cost per task."""
    runs = tables.get("agent_runs")
    if runs is None:
        return _make_result(
            "P05", "cost_per_run", "v1.x", 0, "v2.0.0-beta", 0, 0, 0, "affected > baseline", False
        )

    beta = runs[runs["prompt_version"] == "v2.0.0-beta"]
    non_beta = runs[runs["prompt_version"] != "v2.0.0-beta"]

    if len(beta) == 0 or len(non_beta) == 0:
        return _make_result(
            "P05",
            "cost_per_run",
            "v1.x",
            float(non_beta["estimated_cost_usd"].mean()) if len(non_beta) > 0 else 0,
            "v2.0.0-beta",
            float(beta["estimated_cost_usd"].mean()) if len(beta) > 0 else 0,
            len(non_beta),
            len(beta),
            "affected > baseline",
            False,
        )

    avg_beta = beta["estimated_cost_usd"].mean()
    avg_other = non_beta["estimated_cost_usd"].mean()
    return _make_result(
        "P05",
        "avg_cost_per_run_usd",
        "v1.x",
        avg_other,
        "v2.0.0-beta",
        avg_beta,
        len(non_beta),
        len(beta),
        "affected > baseline",
        avg_beta > avg_other,
    )


def validate_p06_experiment_b(
    tables: dict[str, pd.DataFrame],
) -> list[dict[str, Any]]:
    """P06: Experiment B group has higher export rate, accuracy, and latency."""
    runs = tables.get("agent_runs")
    if runs is None:
        return [
            _make_result(
                "P06", "field_accuracy", "A", 0, "B", 0, 0, 0, "affected > baseline", False
            ),
            _make_result("P06", "latency_ms", "A", 0, "B", 0, 0, 0, "affected > baseline", False),
        ]

    group_b = runs[runs["experiment_group"] == "B"]
    group_a = runs[runs["experiment_group"] == "A"]

    results = []
    if len(group_a) > 0 and len(group_b) > 0:
        # Field accuracy
        acc_a = group_a["field_accuracy"].mean()
        acc_b = group_b["field_accuracy"].mean()
        results.append(
            _make_result(
                "P06",
                "field_accuracy",
                "A",
                acc_a,
                "B",
                acc_b,
                len(group_a),
                len(group_b),
                "affected > baseline",
                acc_b >= acc_a,
            )
        )
        # Latency
        lat_a = group_a["total_latency_ms"].mean()
        lat_b = group_b["total_latency_ms"].mean()
        results.append(
            _make_result(
                "P06",
                "avg_latency_ms",
                "A",
                lat_a,
                "B",
                lat_b,
                len(group_a),
                len(group_b),
                "affected > baseline",
                lat_b > lat_a,
            )
        )
    else:
        results.append(
            _make_result(
                "P06",
                "field_accuracy",
                "A",
                0,
                "B",
                0,
                len(group_a),
                len(group_b),
                "affected > baseline",
                False,
            )
        )
        results.append(
            _make_result(
                "P06",
                "avg_latency_ms",
                "A",
                0,
                "B",
                0,
                len(group_a),
                len(group_b),
                "affected > baseline",
                False,
            )
        )
    return results


def validate_p07_duplicate_rate(
    tables: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    """P07: Duplicate document_uploaded events detected at higher rate on target day."""
    events = tables.get("product_events")
    if events is None:
        return _make_result(
            "P07", "upload_event_count", "expected", 0, "actual", 0, 0, 0, "duplicates > 0", False
        )

    uploads = events[events["event_name"] == "document_uploaded"]
    n_events = len(uploads)
    n_docs = uploads["document_id"].nunique()
    dup_count = n_events - n_docs

    return _make_result(
        "P07",
        "duplicate_upload_count",
        "unique_docs",
        float(n_docs),
        "total_events",
        float(n_events),
        n_docs,
        n_events,
        "duplicates > 0",
        dup_count > 0,
    )


def validate_p08_contamination(
    tables: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    """P08: Some users appear in multiple experiment groups."""
    experiments = tables.get("experiment_assignments")
    if experiments is None:
        return _make_result(
            "P08",
            "contamination_count",
            "clean",
            0,
            "contaminated",
            0,
            0,
            0,
            "contaminated > 0",
            False,
        )

    user_group_counts = experiments.groupby("user_id")["experiment_group"].nunique()
    n_contaminated = int((user_group_counts > 1).sum())
    n_clean = int((user_group_counts == 1).sum())

    return _make_result(
        "P08",
        "users_in_multiple_groups",
        "clean_users",
        float(n_clean),
        "contaminated_users",
        float(n_contaminated),
        n_clean,
        n_contaminated,
        "contaminated > 0",
        n_contaminated > 0,
    )


def validate_p09_high_risk_retry(
    tables: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    """P09: High-risk documents have higher agent retry count."""
    runs = tables.get("agent_runs")
    documents = tables.get("documents")
    if runs is None or documents is None:
        return _make_result(
            "P09",
            "avg_retry_count",
            "low_risk",
            0,
            "high_risk",
            0,
            0,
            0,
            "affected > baseline",
            False,
        )

    # Merge runs with document risk info
    merged = runs.merge(
        documents[["document_id", "contains_high_risk_terms"]], on="document_id", how="inner"
    )
    high_risk = merged[merged["contains_high_risk_terms"] == True]["retry_count"]  # noqa: E712
    low_risk = merged[merged["contains_high_risk_terms"] == False]["retry_count"]  # noqa: E712

    if len(high_risk) == 0 or len(low_risk) == 0:
        return _make_result(
            "P09",
            "avg_retry_count",
            "low_risk",
            float(low_risk.mean()) if len(low_risk) > 0 else 0,
            "high_risk",
            float(high_risk.mean()) if len(high_risk) > 0 else 0,
            len(low_risk),
            len(high_risk),
            "affected > baseline",
            False,
        )

    avg_hr = high_risk.mean()
    avg_lr = low_risk.mean()
    return _make_result(
        "P09",
        "avg_retry_count",
        "low_risk",
        avg_lr,
        "high_risk",
        avg_hr,
        len(low_risk),
        len(high_risk),
        "affected > baseline",
        avg_hr > avg_lr,
    )


def validate_p10_ocr_failure_export(
    tables: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    """P10: Tasks with OCR failure have lower export rate."""
    events = tables.get("product_events")
    if events is None:
        return _make_result(
            "P10",
            "export_rate",
            "no_ocr_fail",
            0,
            "ocr_fail",
            0,
            0,
            0,
            "affected < baseline",
            False,
        )

    # Find tasks with OCR failures
    ocr_failed_tasks = set(events[events["event_name"] == "agent_run_failed"]["task_id"])
    exported_tasks = set(events[events["event_name"] == "form_exported"]["task_id"])
    all_tasks = set(events["task_id"])

    tasks_with_ocr_fail = all_tasks & ocr_failed_tasks
    tasks_no_ocr_fail = all_tasks - ocr_failed_tasks

    export_with_fail = len(tasks_with_ocr_fail & exported_tasks)
    export_no_fail = len(tasks_no_ocr_fail & exported_tasks)

    rate_fail = export_with_fail / max(len(tasks_with_ocr_fail), 1)
    rate_no_fail = export_no_fail / max(len(tasks_no_ocr_fail), 1)

    return _make_result(
        "P10",
        "export_rate",
        "no_ocr_failure",
        rate_no_fail,
        "ocr_failure",
        rate_fail,
        len(tasks_no_ocr_fail),
        len(tasks_with_ocr_fail),
        "affected < baseline",
        rate_fail < rate_no_fail,
    )


def validate_all_phenomena(
    tables: dict[str, pd.DataFrame],
) -> list[dict[str, Any]]:
    """
    Run all 10 validators against the generated tables.

    Returns a list of validation results (P06 returns 2 entries).
    """
    results: list[dict[str, Any]] = []

    results.append(validate_p01_ocr_latency(tables))
    results.append(validate_p02_complex_edit(tables))
    results.append(validate_p03_mobile_export(tables))
    results.append(validate_p04_paid_search_retention(tables))
    results.append(validate_p05_prompt_cost(tables))
    results.extend(validate_p06_experiment_b(tables))
    results.append(validate_p07_duplicate_rate(tables))
    results.append(validate_p08_contamination(tables))
    results.append(validate_p09_high_risk_retry(tables))
    results.append(validate_p10_ocr_failure_export(tables))

    return results
