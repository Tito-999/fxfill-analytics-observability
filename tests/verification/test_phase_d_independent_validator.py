"""Mutation tests for Phase D independent validator."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path.cwd()
VALIDATOR = ROOT / "reports/portfolio/validate_phase_d_evidence.py"
EVIDENCE = ROOT / "reports/portfolio/p2_8_4_phase_d_evidence.json"
HANDOFF = ROOT / "reports/portfolio/p2_8_4_phase_d_handoff.json"
PROBE = ROOT / "reports/portfolio/p2_8_4_phase_d_aggregation_probe.json"
JUNIT = ROOT / "reports/portfolio/p2_8_4_phase_d_pytest.xml"
CORE_ACCEPT = ROOT / "src/fxfill_analytics/verification/core_acceptance.py"
VERIFY_CORE = ROOT / "scripts/verify_core_release.py"
C2_VA = ROOT / "reports/portfolio/p2_8_4_phase_c2_artifact_validation.json"
C2_VAL = ROOT / "reports/portfolio/p2_8_4_phase_c2_validation.json"


def _setup_dir() -> Path:
    d = Path(tempfile.mkdtemp(prefix="phd_mut_"))
    for sub in ["reports/portfolio", "src/fxfill_analytics/verification", "scripts"]:
        (d / sub).mkdir(parents=True, exist_ok=True)
    for src in [
        VALIDATOR,
        EVIDENCE,
        HANDOFF,
        PROBE,
        JUNIT,
        C2_VA,
        C2_VAL,
        CORE_ACCEPT,
        VERIFY_CORE,
    ]:
        if src.exists():
            dst = d / src.relative_to(ROOT)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
    return d


def _run(d: Path, ev_name="p2_8_4_phase_d_evidence.json") -> tuple:
    r = subprocess.run(
        [
            sys.executable,
            str(d / "reports/portfolio/validate_phase_d_evidence.py"),
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
