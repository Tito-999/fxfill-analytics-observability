"""Test Core and Snapshot dbt evidence binding."""

from src.fxfill_analytics.verification.core_acceptance import derive_dbt_model_gate


def valid_dbt():
    return {
        "measurement_completed": True,
        "model_count": 41,
        "model_execution_count": 41,
        "model_success_count": 41,
        "model_fail_count": 0,
        "model_error_count": 0,
        "model_skip_count": 0,
        "model_results_sha256": "c" * 64,
        "test_results_sha256": "d" * 64,
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


class TestCoreSnapshotBinding:
    def test_both_separated_passes(self):
        core_dbt = valid_dbt()
        snap_dbt = valid_dbt()
        assert derive_dbt_model_gate(core_dbt)[0] == "PASS"
        assert derive_dbt_model_gate(snap_dbt)[0] == "PASS"

    def test_core_unseparated_fails(self):
        core_dbt = valid_dbt()
        core_dbt["artifacts_separated"] = False
        core_dbt["artifacts_hashes_distinct"] = False
        assert derive_dbt_model_gate(core_dbt)[0] != "PASS"

    def test_snapshot_unseparated_rejects(self):
        snap_dbt = valid_dbt()
        snap_dbt["artifacts_separated"] = False
        snap_dbt["artifacts_hashes_distinct"] = False
        assert derive_dbt_model_gate(snap_dbt)[0] != "PASS"

    def test_equal_hashes_fails(self):
        d = valid_dbt()
        d["test_results_sha256"] = "c" * 64
        assert derive_dbt_model_gate(d)[0] != "PASS"

    def test_snapshot_hash_mutation_does_not_affect_core(self):
        core_dbt = valid_dbt()
        snap_dbt = valid_dbt()
        snap_dbt["model_results_sha256"] = "z" * 64
        assert derive_dbt_model_gate(core_dbt)[0] == "PASS"
