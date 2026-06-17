"""Mutation tests: verifier must reject bad/forged evidence."""

import json
import sys
import tempfile
from pathlib import Path

import pytest


def _write_temp(name: str, data: dict) -> Path:
    p = Path(tempfile.gettempdir()) / f"mutation_{name}.json"
    with open(p, "w") as f:
        json.dump(data, f)
    return p


def _make_valid_reports(code_commit: str = "a" * 40):
    core = {
        "schema_version": "2.0.0",
        "accepted": True,
        "failed_gates": [],
        "warnings": [],
        "git": {"verified_code_commit": code_commit, "report_generation_head": code_commit},
        "gates": {
            "dbt_models": "PASS",
            "dbt_tests": "PASS",
            "pytest": "PASS",
            "business_metric_integrity": "PASS",
            "strict_reconciliation": "PASS",
            "dashboard_truthfulness": "PASS",
            "streamlit_smoke": "PASS",
            "public_audit": "PASS",
        },
        "dbt": {
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
            "model_results_sha256": "abc123",
            "test_results_sha256": "def456",
            "artifacts_separated": True,
            "measurement_completed": True,
        },
        "engineering": {"collected": 300, "passed": 300, "failed": 0, "errors": 0, "skipped": 0},
        "business_metric_integrity": {"accepted": True, "failures": []},
        "dashboard_truthfulness": {
            "accepted": True,
            "failures": [],
            "retention": {
                "measurement_completed": True,
                "unmatured_points_plotted": 0,
                "empty_traces_rendered": 0,
            },
            "feature_adoption": {
                "measurement_completed": True,
                "metrics_found": 4,
                "database_ui_mismatch_count": 0,
            },
            "agent": {
                "measurement_completed": True,
                "sections_measured": 4,
                "sections_date_filtered": 4,
                "visible_nan_count": 0,
                "visible_none_count": 0,
            },
        },
        "data_quality": {
            "accepted": True,
            "provenance_matches": True,
            "strict_reconciliation_passed": True,
            "measurement_completed": True,
        },
        "dashboard": {"health_http_status": 200},
        "public_release": {"high_severity_findings": 0},
        "clean_build": {},
    }
    snap = {
        "git": {"verified_code_commit": code_commit},
        "provenance": {"provenance_matches": True},
        "dbt": {"model_results_hash": "abc123", "test_results_hash": "def456", "accepted": True},
        "accepted": True,
    }
    truth = {
        "accepted": True,
        "failures": [],
        "retention": {
            "measurement_completed": True,
            "unmatured_points_plotted": 0,
            "empty_traces_rendered": 0,
        },
        "feature_adoption": {
            "measurement_completed": True,
            "metrics_found": 4,
            "database_ui_mismatch_count": 0,
        },
        "agent": {
            "measurement_completed": True,
            "sections_measured": 4,
            "sections_date_filtered": 4,
            "visible_nan_count": 0,
            "visible_none_count": 0,
        },
        "data_quality": {
            "measurement_completed": True,
            "provenance_matches": True,
            "strict_reconciliation_passed": True,
        },
    }
    bi = {"accepted": True, "failures": []}
    return core, snap, truth, bi


def _run_summary(cp, sp, tp, bp, code_commit):
    from scripts.render_acceptance_summary import main

    old_argv = sys.argv
    try:
        sys.argv = [
            "render_acceptance_summary.py",
            "--core-report",
            str(cp),
            "--snapshot",
            str(sp),
            "--truthfulness",
            str(tp),
            "--business-integrity",
            str(bp),
            "--expected-code-commit",
            code_commit,
            "--output-json",
            str(cp.parent / "out.json"),
            "--output-text",
            str(cp.parent / "out.txt"),
        ]
        main()
    finally:
        sys.argv = old_argv


class TestEvidenceMutations:
    def test_mutation_1_wrong_code_commit(self):
        core, snap, truth, bi = _make_valid_reports(code_commit="wrong_commit_here")
        cp, sp, tp, bp = (
            _write_temp("c1", core),
            _write_temp("s1", snap),
            _write_temp("t1", truth),
            _write_temp("b1", bi),
        )
        with pytest.raises(SystemExit) as e:
            _run_summary(cp, sp, tp, bp, "a" * 40)
        assert e.value.code == 1, "Should reject wrong code commit"

    def test_mutation_2_same_model_test_hash(self):
        core, snap, truth, bi = _make_valid_reports()
        core["dbt"]["test_results_sha256"] = "abc123"
        snap["dbt"]["test_results_hash"] = "abc123"
        cp, sp, tp, bp = (
            _write_temp("c2", core),
            _write_temp("s2", snap),
            _write_temp("t2", truth),
            _write_temp("b2", bi),
        )
        with pytest.raises(SystemExit) as e:
            _run_summary(cp, sp, tp, bp, "a" * 40)
        assert e.value.code == 1, "Should reject same hash"

    def test_mutation_3_accepted_with_failures(self):
        core, snap, truth, bi = _make_valid_reports()
        truth["failures"] = ["this is a failure"]
        cp, sp, tp, bp = (
            _write_temp("c3", core),
            _write_temp("s3", snap),
            _write_temp("t3", truth),
            _write_temp("b3", bi),
        )
        with pytest.raises(SystemExit) as e:
            _run_summary(cp, sp, tp, bp, "a" * 40)
        assert e.value.code == 1, "Should reject accepted=true with failures"

    def test_mutation_4_pytest_mismatch(self):
        core, snap, truth, bi = _make_valid_reports()
        core["engineering"]["passed"] = 299
        cp, sp, tp, bp = (
            _write_temp("c4", core),
            _write_temp("s4", snap),
            _write_temp("t4", truth),
            _write_temp("b4", bi),
        )
        with pytest.raises(SystemExit) as e:
            _run_summary(cp, sp, tp, bp, "a" * 40)
        assert e.value.code == 1, "Should reject pytest mismatch"
