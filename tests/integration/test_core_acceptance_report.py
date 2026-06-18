"""Integration tests for core report consistency validation."""

from src.fxfill_analytics.verification.core_acceptance import (
    REQUIRED_GATE_NAMES,
    validate_core_report_consistency,
)


class TestContradictions:
    def test_accepted_true_with_unseparated(self):
        report = {
            "accepted": True,
            "gates": dict.fromkeys(REQUIRED_GATE_NAMES, "PASS"),
            "failed_gates": [],
            "warnings": [],
            "dbt": {
                "measurement_completed": True,
                "model_results_sha256": "a" * 64,
                "test_results_sha256": "b" * 64,
                "artifacts_separated": False,
                "model_count": 41,
                "model_execution_count": 41,
                "model_success_count": 41,
                "model_fail_count": 0,
                "model_error_count": 0,
                "model_skip_count": 0,
                "generic_test_count": 21,
                "singular_test_count": 23,
                "test_definition_count": 44,
                "test_execution_count": 44,
                "test_pass": 44,
                "test_fail": 0,
                "test_error": 0,
                "test_skip": 0,
                "artifacts_paths_distinct": True,
                "artifacts_hashes_distinct": True,
                "artifacts_semantically_distinct": True,
                "failures": [],
            },
        }
        c = validate_core_report_consistency(report)
        assert c["accepted"] is False
        assert c["contradiction_count"] > 0

    def test_accepted_with_same_hash(self):
        report = {
            "accepted": True,
            "gates": dict.fromkeys(REQUIRED_GATE_NAMES, "PASS"),
            "failed_gates": [],
            "warnings": [],
            "dbt": {
                "measurement_completed": True,
                "model_results_sha256": "x" * 64,
                "test_results_sha256": "x" * 64,
                "artifacts_separated": True,
                "model_count": 41,
                "model_execution_count": 41,
                "model_success_count": 41,
                "model_fail_count": 0,
                "model_error_count": 0,
                "model_skip_count": 0,
                "generic_test_count": 21,
                "singular_test_count": 23,
                "test_definition_count": 44,
                "test_execution_count": 44,
                "test_pass": 44,
                "test_fail": 0,
                "test_error": 0,
                "test_skip": 0,
                "artifacts_paths_distinct": True,
                "artifacts_hashes_distinct": True,
                "artifacts_semantically_distinct": True,
                "failures": [],
            },
        }
        c = validate_core_report_consistency(report)
        assert c["accepted"] is False

    def test_accepted_with_warnings(self):
        report = {
            "accepted": True,
            "gates": dict.fromkeys(REQUIRED_GATE_NAMES, "PASS"),
            "failed_gates": [],
            "warnings": ["something"],
            "dbt": {
                "model_results_sha256": "a" * 64,
                "test_results_sha256": "b" * 64,
                "artifacts_separated": True,
                "model_count": 41,
                "model_execution_count": 41,
                "model_success_count": 41,
                "model_fail_count": 0,
                "model_error_count": 0,
                "model_skip_count": 0,
                "generic_test_count": 21,
                "singular_test_count": 23,
                "test_definition_count": 44,
                "test_execution_count": 44,
                "test_pass": 44,
                "test_fail": 0,
                "test_error": 0,
                "test_skip": 0,
                "measurement_completed": True,
                "artifacts_paths_distinct": True,
                "artifacts_hashes_distinct": True,
                "artifacts_semantically_distinct": True,
                "failures": [],
            },
        }
        c = validate_core_report_consistency(report)
        assert c["accepted"] is False

    def test_accepted_with_failed_gates(self):
        report = {
            "accepted": True,
            "gates": dict.fromkeys(REQUIRED_GATE_NAMES, "PASS"),
            "failed_gates": ["bad"],
            "warnings": [],
            "dbt": {
                "model_results_sha256": "a" * 64,
                "test_results_sha256": "b" * 64,
                "artifacts_separated": True,
                "model_count": 41,
                "model_execution_count": 41,
                "model_success_count": 41,
                "model_fail_count": 0,
                "model_error_count": 0,
                "model_skip_count": 0,
                "generic_test_count": 21,
                "singular_test_count": 23,
                "test_definition_count": 44,
                "test_execution_count": 44,
                "test_pass": 44,
                "test_fail": 0,
                "test_error": 0,
                "test_skip": 0,
                "measurement_completed": True,
                "artifacts_paths_distinct": True,
                "artifacts_hashes_distinct": True,
                "artifacts_semantically_distinct": True,
                "failures": [],
            },
        }
        c = validate_core_report_consistency(report)
        assert c["accepted"] is False

    def test_accepted_with_not_run(self):
        report = {
            "accepted": True,
            "gates": dict.fromkeys(list(REQUIRED_GATE_NAMES)[:10], "PASS"),
            "failed_gates": [],
            "warnings": [],
            "dbt": {
                "model_results_sha256": "a" * 64,
                "test_results_sha256": "b" * 64,
                "artifacts_separated": True,
                "model_count": 41,
                "model_execution_count": 41,
                "model_success_count": 41,
                "model_fail_count": 0,
                "model_error_count": 0,
                "model_skip_count": 0,
                "generic_test_count": 21,
                "singular_test_count": 23,
                "test_definition_count": 44,
                "test_execution_count": 44,
                "test_pass": 44,
                "test_fail": 0,
                "test_error": 0,
                "test_skip": 0,
                "measurement_completed": True,
                "artifacts_paths_distinct": True,
                "artifacts_hashes_distinct": True,
                "artifacts_semantically_distinct": True,
                "failures": [],
            },
        }
        c = validate_core_report_consistency(report)
        assert c["accepted"] is False

    def test_consistent_passes(self):
        gates = dict.fromkeys(REQUIRED_GATE_NAMES, "PASS")
        gates["dbt_models"] = "PASS"
        gates["dbt_tests"] = "PASS"
        report = {
            "accepted": True,
            "gates": gates,
            "failed_gates": [],
            "warnings": [],
            "dbt": {
                "measurement_completed": True,
                "model_results_sha256": "a" * 64,
                "test_results_sha256": "b" * 64,
                "artifacts_separated": True,
                "model_count": 41,
                "model_execution_count": 41,
                "model_success_count": 41,
                "model_fail_count": 0,
                "model_error_count": 0,
                "model_skip_count": 0,
                "generic_test_count": 21,
                "singular_test_count": 23,
                "test_definition_count": 44,
                "test_execution_count": 44,
                "test_pass": 44,
                "test_fail": 0,
                "test_error": 0,
                "test_skip": 0,
                "artifacts_paths_distinct": True,
                "artifacts_hashes_distinct": True,
                "artifacts_semantically_distinct": True,
                "failures": [],
            },
        }
        c = validate_core_report_consistency(report)
        assert c["accepted"] is True
        assert c["contradiction_count"] == 0
