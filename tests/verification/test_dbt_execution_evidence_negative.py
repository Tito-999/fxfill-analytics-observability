"""Negative tests: model/test execution evidence must reject errors, unknowns, missing files."""

import json
import tempfile
from pathlib import Path

from src.fxfill_analytics.verification.dbt_artifacts import validate_dbt_artifacts


def _write(path: Path, data: dict):
    path.write_text(json.dumps(data), encoding="utf-8")


def _make_valid() -> tuple[Path, Path, Path, Path]:
    d = Path(tempfile.mkdtemp())
    mr = d / "model_rr.json"
    tr = d / "test_rr.json"
    mm = d / "model_m.json"
    tm = d / "test_m.json"
    _write(
        mr,
        {
            "results": [
                {"unique_id": "model.A", "status": "success"},
                {"unique_id": "model.B", "status": "success"},
            ]
        },
    )
    _write(
        tr,
        {
            "results": [
                {"unique_id": "test.t1", "status": "pass"},
                {"unique_id": "test.t2", "status": "pass"},
            ]
        },
    )
    _write(
        mm,
        {"nodes": {"model.A": {"resource_type": "model"}, "model.B": {"resource_type": "model"}}},
    )
    _write(
        tm, {"nodes": {"test.t1": {"resource_type": "test"}, "test.t2": {"resource_type": "test"}}}
    )
    return mm, mr, tm, tr


class TestModelError:
    def test_model_error_status_fails(self):
        mm, mr, tm, tr = _make_valid()
        _write(
            mr,
            {
                "results": [
                    {"unique_id": "model.A", "status": "success"},
                    {"unique_id": "model.B", "status": "error"},
                ]
            },
        )
        r = validate_dbt_artifacts(
            model_manifest_path=mm,
            model_results_path=mr,
            test_manifest_path=tm,
            test_results_path=tr,
        )
        assert r["model_error_count"] == 1
        assert r["accepted"] is False


class TestMissingFiles:
    def test_missing_model_results_fails(self):
        mm, mr, tm, tr = _make_valid()
        mr.unlink()
        r = validate_dbt_artifacts(
            model_manifest_path=mm,
            model_results_path=mr,
            test_manifest_path=tm,
            test_results_path=tr,
        )
        assert r["model_results_exists"] is False
        assert r["accepted"] is False
        assert "model_results_missing" in r["failures"]


class TestUnknownStatus:
    def test_unknown_model_status_fails(self):
        mm, mr, tm, tr = _make_valid()
        _write(
            mr,
            {
                "results": [
                    {"unique_id": "model.A", "status": "success"},
                    {"unique_id": "model.B", "status": "mystery_status"},
                ]
            },
        )
        r = validate_dbt_artifacts(
            model_manifest_path=mm,
            model_results_path=mr,
            test_manifest_path=tm,
            test_results_path=tr,
        )
        assert "mystery_status" in r["distinct_model_statuses"]
        assert r["accepted"] is False
        assert any("mystery_status" in f for f in r["failures"])


class TestUnknownTestStatus:
    def test_unknown_test_status_fails(self):
        mm, mr, tm, tr = _make_valid()
        _write(
            tr,
            {
                "results": [
                    {"unique_id": "test.t1", "status": "pass"},
                    {"unique_id": "test.t2", "status": "weird"},
                ]
            },
        )
        r = validate_dbt_artifacts(
            model_manifest_path=mm,
            model_results_path=mr,
            test_manifest_path=tm,
            test_results_path=tr,
        )
        assert "weird" in r["distinct_test_statuses"]
        assert r["accepted"] is False
