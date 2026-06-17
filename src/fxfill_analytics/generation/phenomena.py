"""
Configurable business phenomena injection for synthetic data.

All 10 phenomena modify the generated data in specific, detectable ways.
Each phenomenon has: id, enabled flag, date range, affected segment,
configured effect, and expected detectable signal.

Phenomena are injected AFTER base generation so they can be cleanly
toggled on/off for A/B comparison.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

# ── Phenomenon configuration defaults ──
DEFAULT_PHENOMENA: dict[str, dict[str, Any]] = {
    "P01": {
        "id": "P01",
        "name": "OCR latency spike in app v2.3.0",
        "enabled": True,
        "affected_date_range": {"days_ago_start": 14},
        "affected_segment": {"app_version": "2.3.0"},
        "effect_parameter": {"latency_multiplier": 1.8},
        "expected_direction": "P95 OCR latency(v2.3.0) > P95 OCR latency(other versions)",
        "severity": "medium",
    },
    "P02": {
        "id": "P02",
        "name": "Complex documents have higher field edit rates",
        "enabled": True,
        "affected_segment": {"complexity_level": "complex"},
        "effect_parameter": {"edit_rate_multiplier": 2.0},
        "expected_direction": "manual edit rate(complex) > manual edit rate(simple)",
        "severity": "low",
    },
    "P03": {
        "id": "P03",
        "name": "Mobile review-to-export dropoff higher",
        "enabled": True,
        "affected_segment": {"platform": "mobile"},
        "effect_parameter": {"abandonment_multiplier": 1.5},
        "expected_direction": "export rate(mobile) < export rate(desktop)",
        "severity": "medium",
    },
    "P04": {
        "id": "P04",
        "name": "Paid search D7 retention lower",
        "enabled": True,
        "affected_segment": {"acquisition_channel": "paid_search"},
        "effect_parameter": {"d7_retention_multiplier": 0.65},
        "expected_direction": "D7 retention(paid_search) < D7 retention(organic)",
        "severity": "medium",
    },
    "P05": {
        "id": "P05",
        "name": "Prompt v2.0.0-beta has higher token cost, limited quality gain",
        "enabled": True,
        "affected_segment": {"prompt_version": "v2.0.0-beta"},
        "effect_parameter": {"cost_multiplier": 1.35, "quality_improvement": 0.03},
        "expected_direction": "cost per task(v2.0.0-beta) > cost per task(v1.x)",
        "severity": "medium",
    },
    "P06": {
        "id": "P06",
        "name": "Experiment B: higher export rate, higher latency",
        "enabled": True,
        "affected_segment": {"experiment_group": "B"},
        "effect_parameter": {
            "export_rate_uplift": 0.06,
            "field_accuracy_uplift": 0.04,
            "latency_increase_ms": 450,
            "cost_increase_usd": 0.015,
        },
        "expected_direction": "export rate(B) > export rate(A), P95 latency(B) > P95 latency(A)",
        "severity": "medium",
    },
    "P07": {
        "id": "P07",
        "name": "Duplicate document_uploaded events on specific day",
        "enabled": True,
        "affected_date_range": {"day_offset": 45},
        "affected_segment": {"event_name": "document_uploaded"},
        "effect_parameter": {"duplicate_rate": 0.08},
        "expected_direction": "duplicate uploads detected on affected day",
        "severity": "low",
    },
    "P08": {
        "id": "P08",
        "name": "Experiment cross-contamination",
        "enabled": True,
        "affected_segment": {},
        "effect_parameter": {"contamination_rate": 0.03},
        "expected_direction": "some users in both A and B groups",
        "severity": "medium",
    },
    "P09": {
        "id": "P09",
        "name": "High-risk documents have higher agent retry rate",
        "enabled": True,
        "affected_segment": {"contains_high_risk_terms": True},
        "effect_parameter": {"retry_multiplier": 2.5},
        "expected_direction": "retry rate(high-risk) > retry rate(non-high-risk)",
        "severity": "medium",
    },
    "P10": {
        "id": "P10",
        "name": "OCR tool failure drives export rate decline",
        "enabled": True,
        "affected_segment": {"error_type": "ocr_error"},
        "effect_parameter": {"export_rate_penalty": 0.30},
        "expected_direction": "export rate(ocr failure) < export rate(no ocr failure)",
        "severity": "high",
    },
}


def get_enabled_phenomena(
    phenomena_cfg: dict[str, dict[str, Any]] | None = None,
    disabled_ids: list[str] | None = None,
    only_ids: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Return the set of enabled phenomena after applying filters.

    Args:
        phenomena_cfg: Full phenomena config (defaults to DEFAULT_PHENOMENA).
        disabled_ids: Phenomenon IDs to forcibly disable.
        only_ids: If set, only these phenomenon IDs are enabled.

    Returns:
        Dict of enabled phenomena.
    """
    if phenomena_cfg is None:
        phenomena_cfg = dict(DEFAULT_PHENOMENA)

    result: dict[str, dict[str, Any]] = {}
    for pid, cfg in phenomena_cfg.items():
        cfg = dict(cfg)  # copy
        if disabled_ids and pid in disabled_ids:
            cfg["enabled"] = False
        if only_ids is not None and pid not in only_ids:
            cfg["enabled"] = False
        if cfg.get("enabled", False):
            result[pid] = cfg
    return result


def inject_phenomena(
    tables: dict[str, pd.DataFrame],
    rng: np.random.Generator,
    end_date: datetime,
    phenomena_cfg: dict[str, dict[str, Any]] | None = None,
    disabled_ids: list[str] | None = None,
    only_ids: list[str] | None = None,
) -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, Any]]]:
    """
    Apply enabled phenomena to the generated tables.

    Returns:
        Tuple of (modified tables dict, observed signals dict).
    """
    enabled = get_enabled_phenomena(phenomena_cfg, disabled_ids, only_ids)
    observed: dict[str, dict[str, Any]] = {}

    events = tables.get("product_events")
    agent_runs = tables.get("agent_runs")
    experiments = tables.get("experiment_assignments")

    # ── P01: OCR latency spike in v2.3.0 ──
    if "P01" in enabled and events is not None:
        cfg = enabled["P01"]
        days_ago = cfg.get("affected_date_range", {}).get("days_ago_start", 14)
        cutoff = end_date - timedelta(days=days_ago)
        version = cfg.get("affected_segment", {}).get("app_version", "2.3.0")
        multiplier = cfg.get("effect_parameter", {}).get("latency_multiplier", 1.8)

        mask = (
            (events["app_version"] == version)
            & (events["event_time"] >= pd.Timestamp(cutoff))
            & (events["event_name"].isin(["ocr_started", "ocr_completed"]))
        )
        n_affected = mask.sum()
        if n_affected > 0:
            # Convert column to float64 first to avoid dtype incompatibility warning
            events["latency_ms"] = events["latency_ms"].astype(float)
            events.loc[mask, "latency_ms"] = events.loc[mask, "latency_ms"] * multiplier
        observed["P01"] = {
            "affected_rows": int(n_affected),
            "observed_signal": f"Applied {multiplier}x latency multiplier to {n_affected} OCR events",
            "validation_status": "injected",
        }

    # ── P02: Complex documents have higher edit rates ──
    if "P02" in enabled and events is not None:
        documents = tables.get("documents")
        if documents is not None:
            complex_doc_ids = set(
                documents[documents["complexity_level"] == "complex"]["document_id"]
            )
            review_mask = (events["event_name"] == "form_review_started") & events[
                "document_id"
            ].isin(complex_doc_ids)
            review_rows = events[review_mask]
            if len(review_rows) > 0:
                n_tasks = len(review_rows)
                n_extra_per = rng.integers(2, 4, size=n_tasks)
                total_extra = int(n_extra_per.sum())
                ridx = np.repeat(review_rows.index.values, n_extra_per)
                extra_rows = events.loc[ridx].copy()
                extra_rows["event_name"] = "field_edited"
                offsets = np.concatenate([np.arange(c) * rng.uniform(5, 20) for c in n_extra_per])
                extra_rows["event_time"] = extra_rows["event_time"] + pd.to_timedelta(
                    offsets, unit="s"
                )
                extra_rows["latency_ms"] = np.maximum(
                    rng.normal(400, 150, size=total_extra).astype(int), 0
                )
                max_id = len(events)
                extra_rows["event_id"] = [
                    f"EVT_P02_{i:07d}" for i in range(max_id + 1, max_id + 1 + total_extra)
                ]
                events = pd.concat([events, extra_rows], ignore_index=True)
                events = events.sort_values(["task_id", "event_time", "event_id"]).reset_index(
                    drop=True
                )
                tables["product_events"] = events
                observed["P02"] = {
                    "affected_rows": total_extra,
                    "observed_signal": f"{total_extra} extra edits for {n_tasks} complex docs (avg {total_extra/max(n_tasks,1):.1f}/task)",
                    "validation_status": "injected",
                }
        else:
            observed["P02"] = {
                "affected_rows": 0,
                "observed_signal": "No documents table",
                "validation_status": "skipped",
            }

    # ── P03: Mobile review-to-export dropoff (based on user device_type) ──
    if "P03" in enabled and events is not None:
        cfg = enabled["P03"]
        multiplier = cfg.get("effect_parameter", {}).get("abandonment_multiplier", 1.5)
        users_df = tables.get("users")

        if users_df is not None:
            mobile_users = set(users_df[users_df["device_type"] == "mobile"]["user_id"])
            # Find mobile user tasks at review and export stages
            mobile_review_tasks = set(
                events[
                    (events["user_id"].isin(mobile_users))
                    & (events["event_name"] == "form_review_started")
                ]["task_id"]
            )
            mobile_export_tasks = set(
                events[
                    (events["user_id"].isin(mobile_users))
                    & (events["event_name"] == "form_exported")
                ]["task_id"]
            )
            completed_mobile = mobile_review_tasks & mobile_export_tasks
            if len(completed_mobile) > 0:
                n_convert = max(int(len(completed_mobile) * (multiplier - 1.0) * 0.5), 1)
                tasks_to_abandon = sorted(completed_mobile)[:n_convert]
                abandon_mask = (
                    (events["user_id"].isin(mobile_users))
                    & (events["event_name"] == "form_exported")
                    & (events["task_id"].isin(tasks_to_abandon))
                )
                n_affected = abandon_mask.sum()
                if n_affected > 0:
                    events.loc[abandon_mask, "event_name"] = "task_abandoned"
                    events.loc[abandon_mask, "event_status"] = "failure"
            else:
                n_affected = 0
        else:
            n_affected = 0

        observed["P03"] = {
            "affected_rows": int(n_affected),
            "observed_signal": f"Converted {n_affected} mobile-user exports to abandons",
            "validation_status": "injected",
        }

    # ── P04: Paid search D7 retention lower ──
    if "P04" in enabled:
        users_df = tables.get("users")
        sessions_df = tables.get("sessions")
        if users_df is not None:
            cfg = enabled["P04"]
            multiplier = cfg.get("effect_parameter", {}).get("d7_retention_multiplier", 0.65)
            paid_users = set(users_df[users_df["acquisition_channel"] == "paid_search"]["user_id"])
            if sessions_df is not None and len(paid_users) > 0:
                paid_sessions_mask = sessions_df["user_id"].isin(paid_users)
                n_affected = paid_sessions_mask.sum()
                # Reduce page_views for paid_search users' sessions (simulates lower engagement/retention)
                # Do NOT drop sessions — that would break FK integrity
                if n_affected > 0:
                    sessions_df.loc[paid_sessions_mask, "page_views"] = np.maximum(
                        (sessions_df.loc[paid_sessions_mask, "page_views"] * multiplier).astype(
                            int
                        ),
                        1,
                    )
                    tables["sessions"] = sessions_df
                observed["P04"] = {
                    "affected_rows": int(n_affected),
                    "observed_signal": f"Reduced paid_search session page_views by {(1.0 - multiplier) * 100:.0f}%",
                    "validation_status": "injected",
                }
            else:
                observed["P04"] = {
                    "affected_rows": len(paid_users),
                    "observed_signal": "paid_search users identified for lower retention",
                    "validation_status": "injected",
                }
        else:
            observed["P04"] = {
                "affected_rows": 0,
                "observed_signal": "Users table not available",
                "validation_status": "skipped",
            }

    # ── P05: Prompt v2.0.0-beta higher cost ──
    if "P05" in enabled and agent_runs is not None:
        cfg = enabled["P05"]
        prompt = cfg.get("affected_segment", {}).get("prompt_version", "v2.0.0-beta")
        cost_mult = cfg.get("effect_parameter", {}).get("cost_multiplier", 1.35)

        mask = agent_runs["prompt_version"] == prompt
        n_affected = mask.sum()
        if n_affected > 0:
            agent_runs.loc[mask, "estimated_cost_usd"] = (
                agent_runs.loc[mask, "estimated_cost_usd"] * cost_mult
            )
        observed["P05"] = {
            "affected_rows": int(n_affected),
            "observed_signal": f"Applied {cost_mult}x cost to {n_affected} runs with {prompt}",
            "validation_status": "injected",
        }

    # ── P06: Experiment B effects ──
    if "P06" in enabled and agent_runs is not None:
        cfg = enabled["P06"]
        params = cfg.get("effect_parameter", {})
        latency_inc = params.get("latency_increase_ms", 450)
        cost_inc = params.get("cost_increase_usd", 0.015)

        mask = agent_runs["experiment_group"] == "B"
        n_affected = mask.sum()
        if n_affected > 0:
            agent_runs.loc[mask, "total_latency_ms"] = (
                agent_runs.loc[mask, "total_latency_ms"] + latency_inc
            )
            agent_runs.loc[mask, "estimated_cost_usd"] = (
                agent_runs.loc[mask, "estimated_cost_usd"] + cost_inc
            )
            # B group has higher field accuracy
            agent_runs.loc[mask, "field_accuracy"] = np.minimum(
                agent_runs.loc[mask, "field_accuracy"] + 0.04, 1.0
            )
        observed["P06"] = {
            "affected_rows": int(n_affected),
            "observed_signal": f"B group: +{latency_inc}ms latency, +${cost_inc} cost, +0.04 accuracy",
            "validation_status": "injected",
        }

    # ── P07: Duplicate document_uploaded events ──
    if "P07" in enabled and events is not None:
        cfg = enabled["P07"]
        day_offset = cfg.get("affected_date_range", {}).get("day_offset", 45)
        dup_rate = cfg.get("effect_parameter", {}).get("duplicate_rate", 0.08)
        target_date = (end_date - timedelta(days=day_offset)).date()

        # Get events near the target date
        if "event_date" in events.columns:
            # event_date might be datetime or date objects
            target_date_events = events[
                events["event_date"].apply(
                    lambda d: (d.date() if hasattr(d, "date") else d) == target_date
                )
            ]
            target_uploads = target_date_events[
                target_date_events["event_name"] == "document_uploaded"
            ]
            n_to_dup = max(int(len(target_uploads) * dup_rate), 1)

            if n_to_dup > 0 and len(target_uploads) > 0:
                dup_indices = rng.choice(
                    target_uploads.index, size=min(n_to_dup, len(target_uploads)), replace=False
                )
                dups = events.loc[dup_indices].copy()
                # Give duplicates new event IDs
                max_id = len(events)
                dups["event_id"] = [
                    f"EVT_DUP_{i:07d}" for i in range(max_id + 1, max_id + 1 + len(dups))
                ]
                events = pd.concat([events, dups], ignore_index=True)
                events = events.reset_index(drop=True)
                tables["product_events"] = events
                observed["P07"] = {
                    "affected_rows": int(len(dups)),
                    "observed_signal": f"{len(dups)} duplicate uploads on {target_date}",
                    "validation_status": "injected",
                }
        if "P07" not in observed:
            observed["P07"] = {
                "affected_rows": 0,
                "observed_signal": "No matching uploads found for duplicate injection",
                "validation_status": "skipped",
            }

    # ── P08: Experiment cross-contamination ──
    if "P08" in enabled and experiments is not None:
        cfg = enabled["P08"]
        contamination_rate = cfg.get("effect_parameter", {}).get("contamination_rate", 0.03)
        n_contaminate = max(int(len(experiments) * contamination_rate), 1)

        if n_contaminate > 0 and len(experiments) > 1:
            contam_indices = rng.choice(
                experiments.index, size=min(n_contaminate, len(experiments)), replace=False
            )
            duplicates = experiments.loc[contam_indices].copy()
            duplicates["experiment_group"] = duplicates["experiment_group"].apply(
                lambda g: "B" if g == "A" else "A"
            )
            # Set contamination flag on duplicates
            duplicates["is_intentional_contamination"] = True
            # Generate new assignment_ids for duplicates
            max_asgn = len(experiments)
            duplicates["assignment_id"] = [
                f"ASGN_{i:07d}" for i in range(max_asgn + 1, max_asgn + 1 + len(duplicates))
            ]
            experiments = pd.concat([experiments, duplicates], ignore_index=True)

            observed["P08"] = {
                "affected_rows": int(n_contaminate),
                "observed_signal": f"{n_contaminate} users duplicated with opposite group (contamination)",
                "validation_status": "injected",
            }
        tables["experiment_assignments"] = experiments

    # ── P09: High-risk documents → higher retry ──
    if "P09" in enabled and agent_runs is not None:
        cfg = enabled["P09"]
        multiplier = cfg.get("effect_parameter", {}).get("retry_multiplier", 2.5)
        documents = tables.get("documents")
        if documents is not None:
            high_risk_docs = set(documents[documents["contains_high_risk_terms"]]["document_id"])
            mask = agent_runs["document_id"].isin(high_risk_docs)
            n_affected = mask.sum()
            if n_affected > 0:
                agent_runs.loc[mask, "retry_count"] = (
                    agent_runs.loc[mask, "retry_count"] * multiplier
                ).astype(int)
            observed["P09"] = {
                "affected_rows": int(n_affected),
                "observed_signal": f"Applied {multiplier}x retry multiplier to {n_affected} high-risk runs",
                "validation_status": "injected",
            }
        else:
            observed["P09"] = {
                "affected_rows": 0,
                "observed_signal": "No documents table available for P09 injection",
                "validation_status": "skipped",
            }

    # ── P10: OCR failure → lower export rate ──
    if "P10" in enabled and events is not None:
        observed["P10"] = {
            "affected_rows": "pipeline-level",
            "observed_signal": "OCR failures prevent task completion, lowering overall export rate",
            "validation_status": "injected_at_generation",
        }

    return tables, observed
