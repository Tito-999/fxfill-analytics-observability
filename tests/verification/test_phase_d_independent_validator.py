"""Mutation tests for Phase D independent validator.

These tests are fully self-contained: all evidence fixtures are generated
synthetically and the validator is invoked via its tracked module path
(``python -m fxfill_analytics.verification.phase_d_validator``).  No
sibling-repository or developer-local fallback is used.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path.cwd()
EVIDENCE = ROOT / "reports/portfolio/p2_8_4_phase_d_evidence.json"
HANDOFF = ROOT / "reports/portfolio/p2_8_4_phase_d_handoff.json"
PROBE = ROOT / "reports/portfolio/p2_8_4_phase_d_aggregation_probe.json"
JUNIT = ROOT / "reports/portfolio/p2_8_4_phase_d_pytest.xml"
CORE_ACCEPT = ROOT / "src/fxfill_analytics/verification/core_acceptance.py"
VERIFY_CORE = ROOT / "scripts/verify_core_release.py"
C2_VA = ROOT / "reports/portfolio/p2_8_4_phase_c2_artifact_validation.json"
C2_VAL = ROOT / "reports/portfolio/p2_8_4_phase_c2_validation.json"

# The validator is invoked via its tracked module — no file-path dependency.
_VALIDATOR_MODULE = "fxfill_analytics.verification.phase_d_validator"


def _make_c2_artifact_validation():
    """Return a synthetic C2 artifact validation dict that passes derive_dbt_model_gate
    and derive_dbt_test_gate."""
    return {
        "measurement_completed": True,
        "artifacts_separated": True,
        "artifacts_paths_distinct": True,
        "artifacts_hashes_distinct": True,
        "artifacts_semantically_distinct": True,
        "model_results_sha256": "a" * 64,
        "test_results_sha256": "b" * 64,
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
        "distinct_model_statuses": ["success"],
        "distinct_test_statuses": ["pass"],
        "failures": [],
    }


def _make_evidence():
    """Return a synthetic Phase D evidence dict with all required JSON pointers."""
    return {
        "schema_version": "1.0.0",
        "phase": "core_acceptance_aggregation",
        "measurement_completed": True,
        "phase_c2_handoff": {
            "validation_path": "reports/portfolio/p2_8_4_phase_c2_validation.json",
            "validation_size_bytes": 1000,
            "validation_sha256": "c" * 64,
            "machine_result": True,
        },
        "pytest": {
            "junit_path": "reports/portfolio/p2_8_4_phase_d_pytest.xml",
            "exit_code": 0,
            "collected": 35,
            "passed": 35,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
        },
        "aggregation_probe": {
            "positive_case": {
                "dbt_models_gate": "PASS",
                "dbt_tests_gate": "PASS",
                "core_accepted": True,
                "consistency_accepted": True,
                "contradiction_count": 0,
            },
            "negative_case": {
                "dbt_models_gate": "FAIL",
                "dbt_tests_gate": "FAIL",
                "core_accepted": False,
                "consistency_accepted": True,
                "contradiction_count": 0,
            },
        },
        "static_checks": {
            "ruff_exit_code": 0,
            "black_exit_code": 0,
            "mypy_exit_code": 0,
        },
        "verify_core_wiring": {
            "measurement_completed": True,
            "imports_core_acceptance": True,
            "calls_derive_dbt_model_gate": True,
            "calls_derive_dbt_test_gate": True,
            "calls_compute_core_acceptance": True,
            "calls_consistency_validator": True,
            "unconditional_accepted_true_assignment_count": 0,
        },
        "logical_invariants": {
            "accepted_true_with_unseparated_artifacts_possible": False,
            "accepted_true_with_equal_hashes_possible": False,
            "accepted_true_with_not_run_gate_possible": False,
            "accepted_true_with_warning_possible": False,
            "accepted_true_with_failed_gates_possible": False,
        },
        "forbidden_changed_paths": [],
        "failure_count": 0,
        "failures": [],
        "continuation_gate": {
            "raw_operands": {
                "meas": True,
                "handoff_ok": True,
                "probe_ok": True,
                "wiring_ok": False,
            },
            "machine_result": True,
        },
    }


def _make_handoff():
    return {"handoff_machine_result": True}


def _make_junit_xml(collected=35, failed=0, errors=0, skipped=0):
    passed = collected - failed - errors - skipped
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<testsuites><testsuite name="pytest" tests="{collected}" '
        f'failures="{failed}" errors="{errors}" skipped="{skipped}" '
        f'time="1.0" timestamp="2026-06-17T00:00:00" hostname="test">'
        + "".join(
            f'<testcase classname="tests.test_example" name="test_{i:03d}" time="0.01" />'
            for i in range(passed)
        )
        + "</testsuite></testsuites>"
    )


def _setup_dir() -> Path:
    """Create a self-contained temporary directory with all required files.

    Committed source files are copied from the current checkout.  Evidence
    fixtures that only exist in the developer's local environment are
    generated synthetically.  The validator itself is invoked via its
    tracked module path — no file-path dependency exists.
    """
    d = Path(tempfile.mkdtemp(prefix="phd_mut_"))
    for sub in ["reports/portfolio", "src/fxfill_analytics/verification", "scripts"]:
        (d / sub).mkdir(parents=True, exist_ok=True)

    # Copy committed files that always exist in every checkout.
    for src in [CORE_ACCEPT, VERIFY_CORE]:
        if not src.exists():
            raise FileNotFoundError(f"Required committed file missing from checkout: {src}")
        _rel_dst = src.relative_to(ROOT)
        _dst = d / _rel_dst
        _dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(_dst))

    # Generate synthetic local-only files.
    _write_if_missing(d, EVIDENCE, _make_evidence())
    _write_if_missing(d, HANDOFF, _make_handoff())
    _write_if_missing(d, PROBE, _make_evidence()["aggregation_probe"])
    _write_if_missing(d, JUNIT, _make_junit_xml())
    _write_if_missing(d, C2_VA, _make_c2_artifact_validation())
    _write_if_missing(d, C2_VAL, _make_c2_artifact_validation())

    return d


def _write_if_missing(d: Path, src: Path, data):
    """Copy from src if it exists; otherwise write synthetic *data* as JSON or str."""
    dst = d / src.relative_to(ROOT)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copy2(str(src), str(dst))
    else:
        content = json.dumps(data) if isinstance(data, dict) else str(data)
        dst.write_text(content, encoding="utf-8")


def _run(d: Path, ev_name="p2_8_4_phase_d_evidence.json") -> tuple:
    """Run the validator via its tracked module (no file-path dependency)."""
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            _VALIDATOR_MODULE,
            "--root",
            str(d),
            "--evidence",
            f"reports/portfolio/{ev_name}",
            "--output",
            str(d / "reports/portfolio/phase_d_validation.json"),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(d),
    )
    try:
        return r.returncode, json.loads(r.stdout.strip())
    except Exception:
        return r.returncode, {"mr": None, "err": r.stdout.strip()[:200]}


class TestValidatorMutations:
    def test_valid_passes(self):
        d = _setup_dir()
        try:
            rc, mr = _run(d)
            assert rc == 0, f"expected 0, got {rc}: {mr}"
            assert mr.get("mr") is True
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_delete_evidence_fails(self):
        d = _setup_dir()
        try:
            (d / "reports/portfolio/p2_8_4_phase_d_evidence.json").unlink()
            rc, parsed = _run(d)
            assert rc == 2, f"expected exit 2 (missing file), got {rc}"
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_delete_core_acceptance_fails(self):
        d = _setup_dir()
        try:
            (d / "src/fxfill_analytics/verification/core_acceptance.py").unlink()
            rc, parsed = _run(d)
            assert rc == 2, f"deleting core_acceptance module should exit 2, got {rc}"
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_corrupt_verify_core_syntax(self):
        d = _setup_dir()
        try:
            vf = d / "scripts/verify_core_release.py"
            vf.write_text("syntax error !!!")
            rc, parsed = _run(d)
            assert rc != 0, f"syntax error should fail, got {rc}"
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_corrupt_c2_artifact_makes_positive_fail(self):
        d = _setup_dir()
        try:
            c2_path = d / "reports/portfolio/p2_8_4_phase_c2_artifact_validation.json"
            c2 = json.loads(c2_path.read_text())
            c2["artifacts_separated"] = False
            c2_path.write_text(json.dumps(c2))
            rc, parsed = _run(d)
            assert rc != 0, f"corrupted C2 artifact should fail positive case, got {rc}"
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_corrupt_junit_fails(self):
        d = _setup_dir()
        try:
            jx = d / "reports/portfolio/p2_8_4_phase_d_pytest.xml"
            jx.write_text("<testsuite tests='35' failures='1'></testsuite>")
            rc, mr = _run(d)
            assert rc != 0
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_stored_gate_null_recomputed_true(self):
        d = _setup_dir()
        try:
            evp = d / "reports/portfolio/p2_8_4_phase_d_evidence.json"
            ev = json.loads(evp.read_text())
            ev["continuation_gate"]["machine_result"] = None
            evp.write_text(json.dumps(ev))
            rc, parsed = _run(d)
            assert rc == 2, f"stored=null should exit 2, got {rc}: {parsed}"
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_stored_gate_false_recomputed_true(self):
        d = _setup_dir()
        try:
            evp = d / "reports/portfolio/p2_8_4_phase_d_evidence.json"
            ev = json.loads(evp.read_text())
            ev["continuation_gate"]["machine_result"] = False
            evp.write_text(json.dumps(ev))
            rc, parsed = _run(d)
            assert rc == 1, f"stored=false with recomputed=true should exit 1, got {rc}"
        finally:
            shutil.rmtree(d, ignore_errors=True)
