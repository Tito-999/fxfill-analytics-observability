"""Mutation tests for dbt gate derivation — every mutation must fail."""

from src.fxfill_analytics.verification.core_acceptance import (
    derive_dbt_model_gate,
    derive_dbt_test_gate,
)


def valid_dbt():
    return {
        "measurement_completed": True,
        "model_count": 41,
        "model_execution_count": 41,
        "model_success_count": 41,
        "model_fail_count": 0,
        "model_error_count": 0,
        "model_skip_count": 0,
        "model_results_sha256": "a" * 64,
        "test_results_sha256": "b" * 64,
        "artifacts_paths_distinct": True,
        "artifacts_hashes_distinct": True,
        "artifacts_semantically_distinct": True,
        "artifacts_separated": True,
        "generic_test_count": 21,
        "singular_test_count": 23,
        "test_definition_count": 44,
        "test_execution_count": 44,
        "test_pass": 44,
        "test_fail": 0,
        "test_error": 0,
        "test_skip": 0,
        "failures": [],
    }


class TestModelMutations:
    def test_valid_passes(self):
        g, r = derive_dbt_model_gate(valid_dbt())
        assert g == "PASS", f"expected PASS, got {g}: {r}"

    def test_not_separated_fails(self):
        d = valid_dbt()
        d["artifacts_separated"] = False
        assert derive_dbt_model_gate(d)[0] != "PASS"

    def test_same_hash_fails(self):
        d = valid_dbt()
        d["test_results_sha256"] = "a" * 64
        assert derive_dbt_model_gate(d)[0] != "PASS"

    def test_exec_mismatch_fails(self):
        d = valid_dbt()
        d["model_execution_count"] = 40
        assert derive_dbt_model_gate(d)[0] != "PASS"

    def test_success_mismatch_fails(self):
        d = valid_dbt()
        d["model_success_count"] = 40
        assert derive_dbt_model_gate(d)[0] != "PASS"

    def test_fail_nonzero_fails(self):
        d = valid_dbt()
        d["model_fail_count"] = 1
        assert derive_dbt_model_gate(d)[0] != "PASS"

    def test_error_nonzero_fails(self):
        d = valid_dbt()
        d["model_error_count"] = 1
        assert derive_dbt_model_gate(d)[0] != "PASS"

    def test_skip_nonzero_fails(self):
        d = valid_dbt()
        d["model_skip_count"] = 1
        assert derive_dbt_model_gate(d)[0] != "PASS"

    def test_meas_incomplete_not_run(self):
        d = valid_dbt()
        d["measurement_completed"] = False
        assert derive_dbt_model_gate(d)[0] != "PASS"

    def test_sha_none_not_run(self):
        d = valid_dbt()
        d["model_results_sha256"] = None
        g, _ = derive_dbt_model_gate(d)
        assert g != "PASS"

    def test_failures_nonempty_fails(self):
        d = valid_dbt()
        d["failures"] = ["x"]
        assert derive_dbt_model_gate(d)[0] != "PASS"


class TestTestMutations:
    def test_valid_passes(self):
        g, r = derive_dbt_test_gate(valid_dbt())
        assert g == "PASS", f"expected PASS, got {g}: {r}"

    def test_exec_mismatch(self):
        d = valid_dbt()
        d["test_execution_count"] = 43
        assert derive_dbt_test_gate(d)[0] != "PASS"

    def test_fail_nonzero(self):
        d = valid_dbt()
        d["test_fail"] = 1
        assert derive_dbt_test_gate(d)[0] != "PASS"

    def test_not_separated(self):
        d = valid_dbt()
        d["artifacts_separated"] = False
        assert derive_dbt_test_gate(d)[0] != "PASS"

    def test_meas_none_not_run(self):
        d = valid_dbt()
        d["measurement_completed"] = None
        g, _ = derive_dbt_test_gate(d)
        assert g != "PASS"
