"""Unit tests for compute_core_acceptance pure function."""

from src.fxfill_analytics.verification.core_acceptance import (
    REQUIRED_GATE_NAMES,
    compute_core_acceptance,
)


def all_pass_gates():
    return dict.fromkeys(REQUIRED_GATE_NAMES, "PASS")


class TestPositive:
    def test_all_pass_accepted(self):
        r = compute_core_acceptance(gates=all_pass_gates(), failed_gates=[], warnings=[])
        assert r["accepted"] is True
        assert r["pass_gate_count"] == 11
        assert r["fail_gate_count"] == 0
        assert r["not_run_gate_count"] == 0

    def test_all_pass_no_failed(self):
        r = compute_core_acceptance(gates=all_pass_gates(), failed_gates=[], warnings=[])
        assert r["failed_gates"] == []


class TestFail:
    def test_one_fail_rejects(self):
        gates = all_pass_gates()
        gates["dbt_models"] = "FAIL"
        r = compute_core_acceptance(gates=gates, failed_gates=[], warnings=[])
        assert r["accepted"] is False

    def test_not_run_rejects(self):
        gates = all_pass_gates()
        gates["pytest"] = "NOT_RUN"
        r = compute_core_acceptance(gates=gates, failed_gates=[], warnings=[])
        assert r["accepted"] is False
        assert "pytest" in r["not_run_gates"]

    def test_warnings_reject(self):
        r = compute_core_acceptance(gates=all_pass_gates(), failed_gates=[], warnings=["test"])
        assert r["accepted"] is False

    def test_failed_gates_reject(self):
        r = compute_core_acceptance(gates=all_pass_gates(), failed_gates=["bad"], warnings=[])
        assert r["accepted"] is False

    def test_missing_gate_becomes_not_run(self):
        gates = dict.fromkeys(list(REQUIRED_GATE_NAMES)[:10], "PASS")
        r = compute_core_acceptance(gates=gates, failed_gates=[], warnings=[])
        assert r["not_run_gate_count"] >= 1
        assert r["accepted"] is False

    def test_invalid_gate_value(self):
        gates = all_pass_gates()
        gates["dbt_models"] = "TRUE"
        r = compute_core_acceptance(gates=gates, failed_gates=[], warnings=[])
        assert r["gates"]["dbt_models"] == "NOT_RUN"
        assert r["accepted"] is False
