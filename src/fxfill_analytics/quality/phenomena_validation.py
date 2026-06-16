"""
Real observed-signal validators for all 10 business phenomena.

Each validator computes metrics from final generated tables.
No validator reads pre-baked results from configuration.
"""

from __future__ import annotations

from datetime import timedelta
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


# ── P01 ──
def validate_p01_ocr_latency(tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
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
    p95_v230 = float(v230["latency_ms"].quantile(0.95))
    p95_other = float(other["latency_ms"].quantile(0.95))
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


# ── P02 ──
def validate_p02_complex_edit(tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
    events = tables.get("product_events")
    documents = tables.get("documents")
    if events is None or documents is None:
        return _make_result(
            "P02",
            "avg_edits_per_doc",
            "simple",
            0,
            "complex",
            0,
            0,
            0,
            "affected > baseline",
            False,
        )
    field_edits = events[events["event_name"] == "field_edited"]
    if len(field_edits) == 0:
        return _make_result(
            "P02",
            "avg_edits_per_doc",
            "simple",
            0,
            "complex",
            0,
            0,
            0,
            "affected > baseline",
            False,
        )
    edit_counts = field_edits.groupby("document_id").size().reset_index(name="edit_count")
    merged = edit_counts.merge(
        documents[["document_id", "complexity_level"]], on="document_id", how="inner"
    )
    complex_e = merged[merged["complexity_level"] == "complex"]["edit_count"]
    simple_e = merged[merged["complexity_level"] == "simple"]["edit_count"]
    if len(complex_e) == 0 or len(simple_e) == 0:
        return _make_result(
            "P02",
            "avg_edits_per_doc",
            "simple",
            float(simple_e.mean()) if len(simple_e) > 0 else 0,
            "complex",
            float(complex_e.mean()) if len(complex_e) > 0 else 0,
            len(simple_e),
            len(complex_e),
            "affected > baseline",
            False,
        )
    avg_c = float(complex_e.mean())
    avg_s = float(simple_e.mean())
    return _make_result(
        "P02",
        "avg_edits_per_document",
        "simple",
        avg_s,
        "complex",
        avg_c,
        len(simple_e),
        len(complex_e),
        "affected > baseline",
        avg_c > avg_s,
    )


# ── P03: Join with users table to get device_type (not event platform) ──
def validate_p03_mobile_export(tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
    events = tables.get("product_events")
    users = tables.get("users")
    if events is None or users is None:
        return _make_result(
            "P03",
            "review_to_export_rate",
            "desktop",
            0,
            "mobile",
            0,
            0,
            0,
            "affected < baseline",
            False,
        )

    # Join events with users to get device_type
    events_with_device = events.merge(users[["user_id", "device_type"]], on="user_id", how="inner")

    review = events_with_device[events_with_device["event_name"] == "form_review_started"]
    exported = events_with_device[events_with_device["event_name"] == "form_exported"]

    review_desktop = review[review["device_type"] == "desktop"]["task_id"].nunique()
    review_mobile = review[review["device_type"] == "mobile"]["task_id"].nunique()
    export_desktop = exported[exported["device_type"] == "desktop"]["task_id"].nunique()
    export_mobile = exported[exported["device_type"] == "mobile"]["task_id"].nunique()

    if review_desktop == 0 and review_mobile == 0:
        return _make_result(
            "P03",
            "review_to_export_rate",
            "desktop",
            0,
            "mobile",
            0,
            0,
            0,
            "affected < baseline",
            False,
        )

    desktop_rate = export_desktop / max(review_desktop, 1)
    mobile_rate = export_mobile / max(review_mobile, 1)

    return _make_result(
        "P03",
        "review_to_export_rate",
        "desktop",
        desktop_rate,
        "mobile",
        mobile_rate,
        int(review_desktop),
        int(review_mobile),
        "affected < baseline",
        mobile_rate < desktop_rate,
    )


# ── P04: True D7 retention ──
def validate_p04_d7_retention(tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """
    D7 retention: user has at least one event on their signup_date + 7 days.
    Users with < 7 days of observation window are excluded.
    """
    events = tables.get("product_events")
    users = tables.get("users")
    if events is None or users is None:
        return _make_result(
            "P04",
            "d7_retention_rate",
            "organic",
            0,
            "paid_search",
            0,
            0,
            0,
            "affected < baseline",
            False,
        )

    if "event_date" not in events.columns:
        return _make_result(
            "P04",
            "d7_retention_rate",
            "organic",
            0,
            "paid_search",
            0,
            0,
            0,
            "affected < baseline",
            False,
        )

    # Get max event date as end of observation window
    max_event_date = (
        events["event_date"].apply(lambda d: d.date() if hasattr(d, "date") else d).max()
    )

    # Build user signup info
    user_info = users[["user_id", "acquisition_channel", "signup_time"]].copy()
    user_info["signup_date"] = user_info["signup_time"].apply(
        lambda d: d.date() if hasattr(d, "date") else d
    )
    user_info["d7_date"] = user_info["signup_date"] + timedelta(days=7)

    # Exclude users without 7 days of observation
    user_info = user_info[user_info["d7_date"] <= max_event_date]

    # Build user active dates
    events_copy = events.copy()
    events_copy["active_date"] = events_copy["event_date"].apply(
        lambda d: d.date() if hasattr(d, "date") else d
    )
    user_active_dates = events_copy.groupby("user_id")["active_date"].apply(set).reset_index()
    user_active_dates.columns = ["user_id", "active_dates"]

    merged = user_info.merge(user_active_dates, on="user_id", how="inner")

    # D7 retained: user was active on their d7_date
    merged["d7_retained"] = merged.apply(lambda r: r["d7_date"] in r["active_dates"], axis=1)

    organic = merged[merged["acquisition_channel"] == "organic"]
    paid = merged[merged["acquisition_channel"] == "paid_search"]

    if len(organic) == 0 or len(paid) == 0:
        return _make_result(
            "P04",
            "d7_retention_rate",
            "organic",
            float(organic["d7_retained"].mean()) if len(organic) > 0 else 0,
            "paid_search",
            float(paid["d7_retained"].mean()) if len(paid) > 0 else 0,
            len(organic),
            len(paid),
            "affected < baseline",
            False,
        )

    org_rate = float(organic["d7_retained"].mean())
    paid_rate = float(paid["d7_retained"].mean())

    return _make_result(
        "P04",
        "d7_retention_rate",
        "organic",
        org_rate,
        "paid_search",
        paid_rate,
        len(organic),
        len(paid),
        "affected < baseline",
        paid_rate < org_rate,
    )


# ── P05 ──
def validate_p05_prompt_cost(tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
    runs = tables.get("agent_runs")
    if runs is None:
        return _make_result(
            "P05",
            "avg_cost_per_run_usd",
            "v1.x",
            0,
            "v2.0.0-beta",
            0,
            0,
            0,
            "affected > baseline",
            False,
        )
    beta = runs[runs["prompt_version"] == "v2.0.0-beta"]
    non_beta = runs[runs["prompt_version"] != "v2.0.0-beta"]
    if len(beta) == 0 or len(non_beta) == 0:
        return _make_result(
            "P05",
            "avg_cost_per_run_usd",
            "v1.x",
            float(non_beta["estimated_cost_usd"].mean()) if len(non_beta) > 0 else 0,
            "v2.0.0-beta",
            float(beta["estimated_cost_usd"].mean()) if len(beta) > 0 else 0,
            len(non_beta),
            len(beta),
            "affected > baseline",
            False,
        )
    return _make_result(
        "P05",
        "avg_cost_per_run_usd",
        "v1.x",
        float(non_beta["estimated_cost_usd"].mean()),
        "v2.0.0-beta",
        float(beta["estimated_cost_usd"].mean()),
        len(non_beta),
        len(beta),
        "affected > baseline",
        float(beta["estimated_cost_usd"].mean()) > float(non_beta["estimated_cost_usd"].mean()),
    )


# ── P06 ──
def validate_p06_experiment_b(tables: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    runs = tables.get("agent_runs")
    if runs is None:
        return [
            _make_result(
                "P06", "field_accuracy", "A", 0, "B", 0, 0, 0, "affected > baseline", False
            ),
            _make_result(
                "P06", "avg_latency_ms", "A", 0, "B", 0, 0, 0, "affected > baseline", False
            ),
        ]
    gb = runs[runs["experiment_group"] == "B"]
    ga = runs[runs["experiment_group"] == "A"]
    results = []
    if len(ga) > 0 and len(gb) > 0:
        acc_a = float(ga["field_accuracy"].mean())
        acc_b = float(gb["field_accuracy"].mean())
        results.append(
            _make_result(
                "P06",
                "field_accuracy",
                "A",
                acc_a,
                "B",
                acc_b,
                len(ga),
                len(gb),
                "affected > baseline",
                acc_b > acc_a,
            )
        )
        lat_a = float(ga["total_latency_ms"].mean())
        lat_b = float(gb["total_latency_ms"].mean())
        results.append(
            _make_result(
                "P06",
                "avg_latency_ms",
                "A",
                lat_a,
                "B",
                lat_b,
                len(ga),
                len(gb),
                "affected > baseline",
                lat_b > lat_a,
            )
        )
    return results


# ── P07: Day-specific duplicate rate ──
def validate_p07_duplicate_rate(tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
    events = tables.get("product_events")
    if events is None:
        return _make_result(
            "P07", "duplicate_rate", "expected", 0, "actual", 0, 0, 0, "duplicates > 0", False
        )

    uploads = events[events["event_name"] == "document_uploaded"].copy()
    if len(uploads) == 0:
        return _make_result(
            "P07", "duplicate_rate", "expected", 0, "actual", 0, 0, 0, "duplicates > 0", False
        )

    # Normalize event_date
    uploads["evt_date"] = uploads["event_date"].apply(
        lambda d: d.date() if hasattr(d, "date") else d
    )

    # Find the day with the most duplicates
    daily_counts = uploads.groupby("evt_date").agg(
        total_events=("event_id", "count"),
        unique_docs=("document_id", "nunique"),
    )
    daily_counts["duplicates"] = daily_counts["total_events"] - daily_counts["unique_docs"]
    daily_counts["dup_rate"] = daily_counts["duplicates"] / daily_counts["total_events"]

    # Get the day with highest duplicate rate
    max_dup_day = daily_counts["dup_rate"].idxmax()
    max_dup_info = daily_counts.loc[max_dup_day]

    overall_dups = daily_counts["duplicates"].sum()
    overall_total = daily_counts["total_events"].sum()

    return _make_result(
        "P07",
        "affected_day_duplicate_rate",
        "overall_rate",
        round(overall_dups / max(overall_total, 1), 6),
        f"day_{max_dup_day}",
        round(float(max_dup_info["dup_rate"]), 6),
        int(overall_total),
        int(max_dup_info["total_events"]),
        "affected_day_rate ≈ configured 8%",
        float(max_dup_info["dup_rate"]) > 0.05,
    )


# ── P08 ──
def validate_p08_contamination(tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
    experiments = tables.get("experiment_assignments")
    if experiments is None:
        return _make_result(
            "P08",
            "contaminated_users",
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


# ── P09 ──
def validate_p09_high_risk_retry(tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
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
    merged = runs.merge(
        documents[["document_id", "contains_high_risk_terms"]], on="document_id", how="inner"
    )
    high_risk = merged[merged["contains_high_risk_terms"] .eq(True)]["retry_count"]  # noqa: E712
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
    return _make_result(
        "P09",
        "avg_retry_count",
        "low_risk",
        float(low_risk.mean()),
        "high_risk",
        float(high_risk.mean()),
        len(low_risk),
        len(high_risk),
        "affected > baseline",
        float(high_risk.mean()) > float(low_risk.mean()),
    )


# ── P10: Overall export impact and attributable share ──
def validate_p10_ocr_failure_export(tables: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Compute OCR failure rate, overall export rate, and attributable lost-export share."""
    events = tables.get("product_events")
    if events is None:
        return _make_result(
            "P10",
            "export_rate",
            "no_ocr_fail",
            0,
            "with_ocr_fail",
            0,
            0,
            0,
            "affected < baseline",
            False,
        )

    all_tasks = set(events["task_id"])
    ocr_failed_tasks = set(events[events["event_name"] == "agent_run_failed"]["task_id"])
    exported_tasks = set(events[events["event_name"] == "form_exported"]["task_id"])
    n_total = len(all_tasks)
    n_ocr_fail = len(ocr_failed_tasks)
    n_exported = len(exported_tasks)
    n_not_exported = n_total - n_exported

    ocr_failure_rate = n_ocr_fail / max(n_total, 1)
    overall_export_rate = n_exported / max(n_total, 1)

    # Tasks lost after OCR failure: OCR-failed tasks that never exported
    tasks_lost_to_ocr = ocr_failed_tasks - exported_tasks
    n_lost_ocr = len(tasks_lost_to_ocr)

    # OCR attributable share
    ocr_attributable_share = n_lost_ocr / max(n_not_exported, 1)

    return {
        "phenomenon_id": "P10",
        "metric": "overall_export_impact",
        "ocr_failure_rate": round(ocr_failure_rate, 6),
        "overall_export_rate": round(overall_export_rate, 6),
        "total_tasks": n_total,
        "ocr_failed_tasks": n_ocr_fail,
        "exported_tasks": n_exported,
        "tasks_lost_after_ocr_failure": n_lost_ocr,
        "total_not_exported": n_not_exported,
        "ocr_attributable_share": round(ocr_attributable_share, 6),
        "expected_direction": "ocr_attributable_share >= 0.20",
        "passed": ocr_attributable_share >= 0.20 and ocr_failure_rate > 0,
    }


# ── Run all ──
def validate_all_phenomena(tables: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    results.append(validate_p01_ocr_latency(tables))
    results.append(validate_p02_complex_edit(tables))
    results.append(validate_p03_mobile_export(tables))
    results.append(validate_p04_d7_retention(tables))
    results.append(validate_p05_prompt_cost(tables))
    results.extend(validate_p06_experiment_b(tables))
    results.append(validate_p07_duplicate_rate(tables))
    results.append(validate_p08_contamination(tables))
    results.append(validate_p09_high_risk_retry(tables))
    results.append(validate_p10_ocr_failure_export(tables))
    return results
