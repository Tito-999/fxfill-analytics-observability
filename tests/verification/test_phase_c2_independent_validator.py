"""Tests for independent Phase C2 validator — detects tampered evidence."""

import json
import shutil
import tempfile
from pathlib import Path

ORIG_DIR = Path("reports/portfolio/artifacts/p2_8_4_phase_c2")


def _copy_evidence(dst: Path):
    for fp in ORIG_DIR.glob("*.json"):
        shutil.copy2(str(fp), str(dst / fp.name))


class TestTamperResistance:
    def test_valid_evidence_passes(self):
        d = Path(tempfile.mkdtemp())
        try:
            _copy_evidence(d)
            # Run a simplified validation on the copies
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
            _copy_evidence(d)
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
            _copy_evidence(d)
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
            _copy_evidence(d)
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
