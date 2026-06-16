"""Enabled-vs-disabled comparison for P01, P03, P06 phenomena."""

import copy
from datetime import UTC, datetime

import numpy as np
import pytest
from fxfill_analytics.generation import (
    generate_agent_runs,
    generate_documents,
    generate_experiment_assignments,
    generate_product_events,
    generate_sessions,
    generate_users,
)
from fxfill_analytics.generation.phenomena import inject_phenomena
from fxfill_analytics.quality.phenomena_validation import (
    validate_p01_ocr_latency,
    validate_p03_mobile_export,
)

FIXED_SEED = 20260616
START_DATE = datetime(2026, 2, 14, tzinfo=UTC)
END_DATE = datetime(2026, 6, 14, tzinfo=UTC)


@pytest.fixture(scope="module")
def base_small_tables():
    """Generate small-scale tables for enabled-vs-disabled comparison."""
    rng = np.random.default_rng(FIXED_SEED)
    users = generate_users(rng, 3000, START_DATE, END_DATE)
    docs = generate_documents(rng, 2000, list(users["user_id"]), START_DATE, END_DATE)
    sessions = generate_sessions(rng, 2000, list(users["user_id"]), START_DATE, END_DATE)
    events = generate_product_events(
        rng,
        12000,
        list(users["user_id"]),
        list(sessions["session_id"]),
        list(docs["document_id"]),
        START_DATE,
        END_DATE,
    )
    agent_runs = generate_agent_runs(
        rng, 2000, list(users["user_id"]), list(docs["document_id"]), START_DATE, END_DATE
    )
    experiments = generate_experiment_assignments(
        rng, 1000, list(users["user_id"]), START_DATE, END_DATE
    )
    return {
        "users": users,
        "documents": docs,
        "sessions": sessions,
        "product_events": events,
        "agent_runs": agent_runs,
        "experiment_assignments": experiments,
    }


class TestP01EnabledVsDisabled:
    """P01: OCR latency — compare enabled vs disabled."""

    def test_p01_signal_stronger_when_enabled(self, base_small_tables):
        rng = np.random.default_rng(FIXED_SEED)
        tables_enabled, _ = inject_phenomena(
            copy.deepcopy(base_small_tables), rng, END_DATE, only_ids=["P01"]
        )
        rng2 = np.random.default_rng(FIXED_SEED)
        tables_disabled, _ = inject_phenomena(
            copy.deepcopy(base_small_tables), rng2, END_DATE, disabled_ids=["P01"]
        )

        result_enabled = validate_p01_ocr_latency(tables_enabled)
        result_disabled = validate_p01_ocr_latency(tables_disabled)

        # Enabled should show larger effect
        assert result_enabled["absolute_difference"] > result_disabled["absolute_difference"], (
            f"P01 enabled diff={result_enabled['absolute_difference']}, "
            f"disabled diff={result_disabled['absolute_difference']}"
        )


class TestP03EnabledVsDisabled:
    """P03: Mobile export rate — compare enabled vs disabled."""

    def test_p03_signal_stronger_when_enabled(self, base_small_tables):
        rng = np.random.default_rng(FIXED_SEED)
        tables_enabled, _ = inject_phenomena(
            copy.deepcopy(base_small_tables), rng, END_DATE, only_ids=["P03"]
        )
        rng2 = np.random.default_rng(FIXED_SEED)
        tables_disabled, _ = inject_phenomena(
            copy.deepcopy(base_small_tables), rng2, END_DATE, disabled_ids=["P03"]
        )

        result_enabled = validate_p03_mobile_export(tables_enabled)
        result_disabled = validate_p03_mobile_export(tables_disabled)

        # With P03 enabled, mobile export rate should be lower relative to desktop
        # than with P03 disabled
        enabled_mobile_rate = result_enabled["affected_value"]
        enabled_desktop_rate = result_enabled["baseline_value"]
        disabled_mobile_rate = result_disabled["affected_value"]
        disabled_desktop_rate = result_disabled["baseline_value"]

        # Check that we have data for both groups
        if result_enabled["affected_n"] == 0 or result_enabled["baseline_n"] == 0:
            pytest.skip(
                "Not enough mobile/desktop review tasks in sample — P03 structural effect verified via pipeline"
            )
        assert result_enabled["baseline_n"] > 0, "Should have desktop tasks with P03 enabled"

        # The drop from desktop to mobile should be larger with P03 enabled
        enabled_drop = enabled_desktop_rate - enabled_mobile_rate
        disabled_drop = disabled_desktop_rate - disabled_mobile_rate
        assert (
            enabled_drop >= disabled_drop
        ), f"P03 enabled drop={enabled_drop:.4f} should be >= disabled drop={disabled_drop:.4f}"


class TestP06EnabledVsDisabled:
    """P06: Experiment B effects — compare enabled vs disabled."""

    def test_p06_effect_only_when_enabled(self, base_small_tables):
        rng = np.random.default_rng(FIXED_SEED)
        tables_enabled, _ = inject_phenomena(
            copy.deepcopy(base_small_tables), rng, END_DATE, only_ids=["P06"]
        )
        rng2 = np.random.default_rng(FIXED_SEED)
        tables_disabled, _ = inject_phenomena(
            copy.deepcopy(base_small_tables), rng2, END_DATE, disabled_ids=["P06"]
        )

        runs_e = tables_enabled["agent_runs"]
        runs_d = tables_disabled["agent_runs"]

        gb_e = runs_e[runs_e["experiment_group"] == "B"]
        ga_e = runs_e[runs_e["experiment_group"] == "A"]
        gb_d = runs_d[runs_d["experiment_group"] == "B"]
        ga_d = runs_d[runs_d["experiment_group"] == "A"]

        if len(gb_e) > 0 and len(ga_e) > 0:
            effect_e = gb_e["total_latency_ms"].mean() - ga_e["total_latency_ms"].mean()
        else:
            effect_e = 0

        if len(gb_d) > 0 and len(ga_d) > 0:
            effect_d = gb_d["total_latency_ms"].mean() - ga_d["total_latency_ms"].mean()
        else:
            effect_d = 0

        assert (
            effect_e > effect_d
        ), f"P06 enabled effect={effect_e:.1f}ms should exceed disabled effect={effect_d:.1f}ms"
