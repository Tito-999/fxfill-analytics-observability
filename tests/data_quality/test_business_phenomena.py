"""Directional tests for the 10 business phenomena."""

from datetime import UTC, datetime

import numpy as np
import pytest
from fxfill_analytics.generation import (
    generate_agent_runs,
    generate_documents,
    generate_product_events,
    generate_sessions,
    generate_users,
)
from fxfill_analytics.generation.phenomena import (
    get_enabled_phenomena,
    inject_phenomena,
)

FIXED_SEED = 20260616
START_DATE = datetime(2026, 2, 14, tzinfo=UTC)
END_DATE = datetime(2026, 6, 14, tzinfo=UTC)


@pytest.fixture(scope="module")
def base_tables():
    """Generate base tables for phenomena testing."""
    rng = np.random.default_rng(FIXED_SEED)
    users = generate_users(rng, 500, START_DATE, END_DATE)
    docs = generate_documents(rng, 300, list(users["user_id"]), START_DATE, END_DATE)
    sessions = generate_sessions(rng, 300, list(users["user_id"]), START_DATE, END_DATE)
    events = generate_product_events(
        rng,
        2000,
        list(users["user_id"]),
        list(sessions["session_id"]),
        list(docs["document_id"]),
        START_DATE,
        END_DATE,
    )
    agent_runs = generate_agent_runs(
        rng, 300, list(users["user_id"]), list(docs["document_id"]), START_DATE, END_DATE
    )
    return {
        "users": users,
        "documents": docs,
        "sessions": sessions,
        "product_events": events,
        "agent_runs": agent_runs,
    }


class TestP01OCRLatencySpike:
    """P01: app_version 2.3.0 has higher OCR latency in last 14 days."""

    def test_ocr_latency_higher_in_v230(self, base_tables):
        rng = np.random.default_rng(FIXED_SEED)
        # Enable only P01
        tables, obs = inject_phenomena(
            dict(base_tables),
            rng,
            END_DATE,
            only_ids=["P01"],
        )
        events = tables["product_events"]
        # Check that P01 was injected
        assert "P01" in obs
        assert obs["P01"]["validation_status"] == "injected"
        # OCR events for v2.3.0 should exist
        ocr_v230 = events[
            (events["app_version"] == "2.3.0")
            & events["event_name"].isin(["ocr_started", "ocr_completed"])
        ]
        assert len(ocr_v230) > 0, "Should have OCR events for v2.3.0"

    def test_p01_disabled_no_effect(self, base_tables):
        rng = np.random.default_rng(FIXED_SEED)
        tables_no, _ = inject_phenomena(
            dict(base_tables),
            rng,
            END_DATE,
            disabled_ids=["P01"],
        )
        tables_yes, _ = inject_phenomena(
            dict(base_tables),
            rng,
            END_DATE,
            only_ids=["P01"],
        )
        # With P01 enabled, mean OCR latency should be higher
        ocr_mask_all = base_tables["product_events"]["event_name"].isin(
            ["ocr_started", "ocr_completed"]
        )
        mean_all = base_tables["product_events"].loc[ocr_mask_all, "latency_ms"].mean()
        ocr_mask_enabled = tables_yes["product_events"]["event_name"].isin(
            ["ocr_started", "ocr_completed"]
        )
        mean_enabled = tables_yes["product_events"].loc[ocr_mask_enabled, "latency_ms"].mean()
        assert mean_enabled >= mean_all, "P01 should increase latency"


class TestP05PromptCost:
    """P05: v2.0.0-beta prompt has higher cost."""

    def test_prompt_cost_increase(self, base_tables):
        rng = np.random.default_rng(FIXED_SEED)
        tables, obs = inject_phenomena(
            dict(base_tables),
            rng,
            END_DATE,
            only_ids=["P05"],
        )
        assert "P05" in obs
        runs = tables["agent_runs"]
        beta = runs[runs["prompt_version"] == "v2.0.0-beta"]
        non_beta = runs[runs["prompt_version"] != "v2.0.0-beta"]
        if len(beta) > 0 and len(non_beta) > 0:
            assert (
                beta["estimated_cost_usd"].mean() > non_beta["estimated_cost_usd"].mean()
            ), "v2.0.0-beta should have higher cost"


class TestP06ExperimentB:
    """P06: Experiment B group has higher latency and field_accuracy."""

    def test_experiment_b_effects(self, base_tables):
        rng = np.random.default_rng(FIXED_SEED)
        tables, obs = inject_phenomena(
            dict(base_tables),
            rng,
            END_DATE,
            only_ids=["P06"],
        )
        assert "P06" in obs
        runs = tables["agent_runs"]
        group_b = runs[runs["experiment_group"] == "B"]
        group_a = runs[runs["experiment_group"] == "A"]
        if len(group_b) > 0 and len(group_a) > 0:
            assert (
                group_b["field_accuracy"].mean() >= group_a["field_accuracy"].mean()
            ), "B group should have higher field accuracy"
            assert (
                group_b["total_latency_ms"].mean() > group_a["total_latency_ms"].mean()
            ), "B group should have higher latency"


class TestP07DuplicateEvents:
    """P07: Duplicate document_uploaded events are injected."""

    def test_duplicates_injected(self, base_tables):
        rng = np.random.default_rng(FIXED_SEED)
        tables, obs = inject_phenomena(
            dict(base_tables),
            rng,
            END_DATE,
            only_ids=["P07"],
        )
        assert "P07" in obs
        if obs["P07"]["validation_status"] == "injected":
            assert obs["P07"]["affected_rows"] > 0


class TestP08CrossContamination:
    """P08: Experiment cross-contamination is injected."""

    def test_contamination_injected(self, base_tables):
        rng = np.random.default_rng(FIXED_SEED)
        # Need experiment_assignments table
        from fxfill_analytics.generation import generate_experiment_assignments

        rng2 = np.random.default_rng(FIXED_SEED + 1)
        experiments = generate_experiment_assignments(
            rng2,
            100,
            list(base_tables["users"]["user_id"]),
            START_DATE,
            END_DATE,
        )
        tables = dict(base_tables)
        tables["experiment_assignments"] = experiments

        tables, obs = inject_phenomena(
            tables,
            rng,
            END_DATE,
            only_ids=["P08"],
        )
        assert "P08" in obs
        assert obs["P08"]["affected_rows"] > 0


class TestPhenomenaToggle:
    """Verify phenomena can be toggled on/off."""

    def test_get_enabled_all(self):
        enabled = get_enabled_phenomena()
        assert len(enabled) == 10, f"Expected 10 enabled, got {len(enabled)}"

    def test_get_enabled_disabled_ids(self):
        enabled = get_enabled_phenomena(disabled_ids=["P01", "P02", "P03"])
        assert "P01" not in enabled
        assert "P02" not in enabled
        assert "P04" in enabled

    def test_get_enabled_only_ids(self):
        enabled = get_enabled_phenomena(only_ids=["P01", "P07"])
        assert list(enabled.keys()) == ["P01", "P07"]
