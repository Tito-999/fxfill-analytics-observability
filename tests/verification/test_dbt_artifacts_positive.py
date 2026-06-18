"""Positive test: validate_dbt_artifacts accepts correct separated artifacts."""

import json
import tempfile
from pathlib import Path

from src.fxfill_analytics.verification.dbt_artifacts import validate_dbt_artifacts


def _write(path: Path, data: dict):
    path.write_text(json.dumps(data), encoding="utf-8")


def test_positive_valid_artifacts():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        mr = d / "model_rr.json"
        tr = d / "test_rr.json"
        mm = d / "model_manifest.json"
        tm = d / "test_manifest.json"

        # 2 models, both successful
        _write(
            mr,
            {
                "results": [
                    {"unique_id": "model.A", "status": "success"},
                    {"unique_id": "model.B", "status": "success"},
                ]
            },
        )
        # Model manifest
        _write(
            mm,
            {
                "nodes": {
                    "model.A": {"resource_type": "model"},
                    "model.B": {"resource_type": "model"},
                }
            },
        )

        # 3 tests all pass: 2 generic, 1 singular
        _write(
            tr,
            {
                "results": [
                    {"unique_id": "test.not_null_a", "status": "pass"},
                    {"unique_id": "test.unique_b", "status": "pass"},
                    {"unique_id": "test.custom_sql", "status": "pass"},
                ]
            },
        )
        _write(
            tm,
            {
                "nodes": {
                    "test.not_null_a": {
                        "resource_type": "test",
                        "test_metadata": {"name": "not_null_a"},
                    },
                    "test.unique_b": {
                        "resource_type": "test",
                        "test_metadata": {"name": "unique_b"},
                    },
                    "test.custom_sql": {"resource_type": "test"},
                }
            },
        )

        r = validate_dbt_artifacts(
            model_manifest_path=mm,
            model_results_path=mr,
            test_manifest_path=tm,
            test_results_path=tr,
        )

        assert (
            r["model_count"] == 2
        ), f"model_count={r['model_count']} mm={mm} mm_exists={mm.exists()} mr_exists={mr.exists()} failures={r['failures']}"
        assert r["model_execution_count"] == 2
        assert r["model_success_count"] == 2
        assert r["model_fail_count"] == 0
        assert r["model_error_count"] == 0

        assert r["generic_test_count"] == 2
        assert r["singular_test_count"] == 1
        assert r["test_definition_count"] == 3
        assert r["test_execution_count"] == 3
        assert r["test_pass"] == 3
        assert r["test_fail"] == 0
        assert r["test_error"] == 0
        assert r["test_skip"] == 0

        assert r["artifacts_paths_distinct"] is True
        assert r["artifacts_hashes_distinct"] is True
        assert r["artifacts_semantically_distinct"] is True
        assert r["artifacts_separated"] is True
        assert r["accepted"] is True
        assert r["failures"] == []
