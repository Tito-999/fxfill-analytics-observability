"""Unit tests for Phase C2 gate computation — prevents null→true regression."""


def make_valid_evidence() -> dict:
    return {
        "measurement_completed": True,
        "probe": {
            "generate_data_exit_code": 0,
            "build_warehouse_exit_code": 0,
            "dbt_run_exit_code": 0,
            "dbt_test_exit_code": 0,
            "artifact_validation_exit_code": 0,
            "database_size_bytes_before_cleanup": 274432,
            "database_sha256_before_cleanup": "a" * 64,
            "run_id_matches": True,
            "config_hash_matches": True,
        },
        "model_checkpoint": {
            "written_before_dbt_test": True,
            "model_results_unchanged_after_test": True,
        },
        "stable_artifacts": {"all_files_exist": True, "all_copy_hashes_match": True},
        "artifact_validation": {
            "measurement_completed": True,
            "model_results_sha256": "b" * 64,
            "test_results_sha256": "c" * 64,
            "artifacts_paths_distinct": True,
            "artifacts_hashes_distinct": True,
            "artifacts_semantically_distinct": True,
            "artifacts_separated": True,
            "accepted": True,
            "failures": [],
        },
        "failure_count": 0,
        "failures": [],
    }


def compute_gate(ev: dict):
    try:
        mc = ev["measurement_completed"] is True
        p = ev["probe"]
        # Required fields: any None → gate None
        req = [
            p["generate_data_exit_code"],
            p["build_warehouse_exit_code"],
            p["dbt_run_exit_code"],
            p["dbt_test_exit_code"],
            p["artifact_validation_exit_code"],
            p["database_size_bytes_before_cleanup"],
            p["database_sha256_before_cleanup"],
            p["run_id_matches"],
            p["config_hash_matches"],
            ev["model_checkpoint"]["written_before_dbt_test"],
            ev["model_checkpoint"]["model_results_unchanged_after_test"],
            ev["stable_artifacts"]["all_files_exist"],
            ev["stable_artifacts"]["all_copy_hashes_match"],
            ev["artifact_validation"]["measurement_completed"],
            ev["artifact_validation"]["model_results_sha256"],
            ev["artifact_validation"]["test_results_sha256"],
            ev["artifact_validation"]["artifacts_paths_distinct"],
            ev["artifact_validation"]["artifacts_hashes_distinct"],
            ev["artifact_validation"]["artifacts_semantically_distinct"],
            ev["artifact_validation"]["artifacts_separated"],
            ev["artifact_validation"]["accepted"],
            ev["artifact_validation"]["failures"],
            ev["failure_count"],
            ev["failures"],
        ]
        if any(v is None for v in req):
            return None
        # Compute gate
        av = ev["artifact_validation"]
        g = p["generate_data_exit_code"] == 0 and p["build_warehouse_exit_code"] == 0
        g = g and p["dbt_run_exit_code"] == 0 and p["dbt_test_exit_code"] == 0
        g = g and p["artifact_validation_exit_code"] == 0
        g = g and p["database_size_bytes_before_cleanup"] > 0
        g = g and len(p["database_sha256_before_cleanup"]) == 64
        g = g and p["run_id_matches"] is True and p["config_hash_matches"] is True
        g = g and ev["model_checkpoint"]["written_before_dbt_test"] is True
        g = g and ev["model_checkpoint"]["model_results_unchanged_after_test"] is True
        g = g and ev["stable_artifacts"]["all_files_exist"] is True
        g = g and ev["stable_artifacts"]["all_copy_hashes_match"] is True
        g = g and av["measurement_completed"] is True
        g = g and av["model_results_sha256"] != av["test_results_sha256"]
        g = g and av["artifacts_paths_distinct"] is True
        g = g and av["artifacts_hashes_distinct"] is True
        g = g and av["artifacts_semantically_distinct"] is True
        g = g and av["artifacts_separated"] is True
        g = g and av["accepted"] is True and av["failures"] == []
        g = g and ev["failure_count"] == 0 and ev["failures"] == []
        return mc and g
    except (KeyError, TypeError):
        return None


class TestGateNull:
    def test_gen_null_returns_none(self):
        ev = make_valid_evidence()
        ev["probe"]["generate_data_exit_code"] = None
        assert compute_gate(ev) is None

    def test_wh_null_returns_none(self):
        ev = make_valid_evidence()
        ev["probe"]["build_warehouse_exit_code"] = None
        assert compute_gate(ev) is None

    def test_db_size_null_returns_none(self):
        ev = make_valid_evidence()
        ev["probe"]["database_size_bytes_before_cleanup"] = None
        assert compute_gate(ev) is None

    def test_db_size_zero_returns_false(self):
        ev = make_valid_evidence()
        ev["probe"]["database_size_bytes_before_cleanup"] = 0
        assert compute_gate(ev) is False

    def test_same_hashes_returns_false(self):
        ev = make_valid_evidence()
        ev["artifact_validation"]["model_results_sha256"] = "d" * 64
        ev["artifact_validation"]["test_results_sha256"] = "d" * 64
        assert compute_gate(ev) is False

    def test_stable_missing_returns_false(self):
        ev = make_valid_evidence()
        ev["stable_artifacts"]["all_files_exist"] = False
        assert compute_gate(ev) is False

    def test_run_id_mismatch_returns_false(self):
        ev = make_valid_evidence()
        ev["probe"]["run_id_matches"] = False
        assert compute_gate(ev) is False

    def test_config_hash_mismatch_returns_false(self):
        ev = make_valid_evidence()
        ev["probe"]["config_hash_matches"] = False
        assert compute_gate(ev) is False

    def test_all_valid_returns_true(self):
        assert compute_gate(make_valid_evidence()) is True
