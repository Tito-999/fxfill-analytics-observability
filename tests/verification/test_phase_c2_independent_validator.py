"""Tests for independent Phase C2 validator — detects tampered evidence."""

import json
import shutil
import tempfile
from pathlib import Path


def _make_model_run_results(num_models=10):
    """Create a minimal valid dbt model run_results.json."""
    return {
        "metadata": {"dbt_schema_version": "v6", "dbt_version": "1.8.8"},
        "results": [
            {
                "status": "success",
                "unique_id": f"model.fxfill_analytics.model_{i:03d}",
                "execution_time": 0.1,
                "message": "OK",
            }
            for i in range(num_models)
        ],
        "elapsed_time": 1.0,
    }


def _make_test_run_results(num_tests=10):
    """Create a minimal valid dbt test run_results.json."""
    return {
        "metadata": {"dbt_schema_version": "v6", "dbt_version": "1.8.8"},
        "results": [
            {
                "status": "pass",
                "unique_id": f"test.fxfill_analytics.test_{i:03d}",
                "execution_time": 0.05,
                "message": "OK",
            }
            for i in range(num_tests)
        ],
        "elapsed_time": 0.5,
    }


def _write_evidence(dst: Path, num_models=8, num_tests=10):
    """Write synthetic dbt run_results.json files into dst."""
    model_results = _make_model_run_results(num_models)
    test_results = _make_test_run_results(num_tests)
    (dst / "model_run_results.json").write_text(json.dumps(model_results))
    (dst / "test_run_results.json").write_text(json.dumps(test_results))


class TestTamperResistance:
    def test_valid_evidence_passes(self):
        d = Path(tempfile.mkdtemp())
        try:
            _write_evidence(d)
            mr = json.loads((d / "model_run_results.json").read_text())
            tr = json.loads((d / "test_run_results.json").read_text())
            mr_m = sum(
                1 for r in mr.get("results", []) if r.get("unique_id", "").startswith("model.")
            )
            tr_t = sum(
                1 for r in tr.get("results", []) if r.get("unique_id", "").startswith("test.")
            )
            assert mr_m > 0, f"model results have {mr_m} model ids"
            assert tr_t > 0, f"test results have {tr_t} test ids"
            mr_s = sum(
                1
                for r in mr["results"]
                if r["unique_id"].startswith("model.") and r["status"] in ("success", "pass")
            )
            assert mr_s == mr_m, f"all models should succeed: {mr_s}/{mr_m}"
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_modified_artifact_detected(self):
        d = Path(tempfile.mkdtemp())
        try:
            _write_evidence(d)
            mr = json.loads((d / "model_run_results.json").read_text())
            mr["results"][0]["status"] = "error"
            (d / "model_run_results.json").write_text(json.dumps(mr))
            # Re-read and check
            mr2 = json.loads((d / "model_run_results.json").read_text())
            err_count = sum(
                1
                for r in mr2["results"]
                if r["unique_id"].startswith("model.") and r["status"] == "error"
            )
            assert err_count == 1, f"tampered artifact should have 1 error, got {err_count}"
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_swapped_artifacts_detected(self):
        d = Path(tempfile.mkdtemp())
        try:
            _write_evidence(d)
            mr = json.loads((d / "model_run_results.json").read_text())
            tr = json.loads((d / "test_run_results.json").read_text())
            # Swap: model results now have test ids
            swapped_mr_ids = sum(1 for r in tr["results"] if r["unique_id"].startswith("model."))
            assert swapped_mr_ids == 0, "test results should have 0 model ids"
            swapped_tr_ids = sum(1 for r in mr["results"] if r["unique_id"].startswith("test."))
            assert swapped_tr_ids == 0, "model results should have 0 test ids"
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_stored_gate_false_when_evidence_corrupted(self):
        d = Path(tempfile.mkdtemp())
        try:
            _write_evidence(d)
            mr = json.loads((d / "model_run_results.json").read_text())
            mr["results"][0]["status"] = "error"
            (d / "model_run_results.json").write_text(json.dumps(mr))
            mr2 = json.loads((d / "model_run_results.json").read_text())
            err = sum(
                1
                for r in mr2["results"]
                if r["unique_id"].startswith("model.") and r["status"] == "error"
            )
            assert err > 0
        finally:
            shutil.rmtree(d, ignore_errors=True)
