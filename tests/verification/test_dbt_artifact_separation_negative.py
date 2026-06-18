"""Negative tests: validate_dbt_artifacts must reject invalid artifact configurations."""

import json
import tempfile
from pathlib import Path

from src.fxfill_analytics.verification.dbt_artifacts import validate_dbt_artifacts


def _write(path: Path, data: dict):
    path.write_text(json.dumps(data), encoding="utf-8")


class TestSamePath:
    def test_rejects_same_model_test_path(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            mr = d / "rr.json"
            mm = d / "m.json"
            _write(mr, {"results": [{"unique_id": "model.A", "status": "success"}]})
            _write(mm, {"nodes": {"model.A": {"resource_type": "model"}}})
            r = validate_dbt_artifacts(
                model_manifest_path=mm,
                model_results_path=mr,
                test_manifest_path=mm,
                test_results_path=mr,
            )
            assert (
                r["artifacts_paths_distinct"] is False
            ), f"paths_distinct={r['artifacts_paths_distinct']}"
            assert r["artifacts_separated"] is False
            assert r["accepted"] is False
            assert len(r["failures"]) > 0


class TestSameContent:
    def test_rejects_identical_content(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            mr = d / "model_rr.json"
            tr = d / "test_rr.json"
            mm = d / "model_manifest.json"
            tm = d / "test_manifest.json"
            content = {"results": [{"unique_id": "model.A", "status": "success"}]}
            _write(mr, content)
            _write(tr, content)
            _write(mm, {"nodes": {"model.A": {"resource_type": "model"}}})
            _write(tm, {"nodes": {"test.t1": {"resource_type": "test"}}})
            r = validate_dbt_artifacts(
                model_manifest_path=mm,
                model_results_path=mr,
                test_manifest_path=tm,
                test_results_path=tr,
            )
            assert r["artifacts_paths_distinct"] is True
            assert r["artifacts_hashes_distinct"] is False
            assert r["artifacts_separated"] is False
            assert r["accepted"] is False


class TestModelArtifactOnlyTests:
    def test_model_artifact_only_test_ids(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            mr = d / "model_rr.json"
            tr = d / "test_rr.json"
            mm = d / "model_m.json"
            tm = d / "test_m.json"
            _write(mr, {"results": [{"unique_id": "test.x", "status": "pass"}]})
            _write(tr, {"results": [{"unique_id": "test.y", "status": "pass"}]})
            _write(mm, {"nodes": {"model.A": {"resource_type": "model"}}})
            _write(
                tm,
                {
                    "nodes": {
                        "test.x": {"resource_type": "test"},
                        "test.y": {"resource_type": "test"},
                    }
                },
            )
            r = validate_dbt_artifacts(
                model_manifest_path=mm,
                model_results_path=mr,
                test_manifest_path=tm,
                test_results_path=tr,
            )
            assert r["model_artifact_model_ids"] == 0
            assert r["model_artifact_test_ids"] > 0
            assert r["artifacts_semantically_distinct"] is False
            assert r["accepted"] is False


class TestTestArtifactOnlyModels:
    def test_test_artifact_only_model_ids(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            mr = d / "model_rr.json"
            tr = d / "test_rr.json"
            mm = d / "model_m.json"
            tm = d / "test_m.json"
            _write(mr, {"results": [{"unique_id": "model.A", "status": "success"}]})
            _write(tr, {"results": [{"unique_id": "model.B", "status": "success"}]})
            _write(
                mm,
                {
                    "nodes": {
                        "model.A": {"resource_type": "model"},
                        "model.B": {"resource_type": "model"},
                    }
                },
            )
            _write(tm, {"nodes": {}})
            r = validate_dbt_artifacts(
                model_manifest_path=mm,
                model_results_path=mr,
                test_manifest_path=tm,
                test_results_path=tr,
            )
            assert r["test_artifact_test_ids"] == 0
            assert r["test_artifact_model_ids"] > 0
            assert r["accepted"] is False
