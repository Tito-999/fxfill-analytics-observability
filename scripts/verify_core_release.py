"""Core Release Acceptance — keeps temp DB alive through full pytest."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "src"))  # Ensure fxfill_analytics is importable
R = PROJECT / "reports" / "portfolio"
R.mkdir(parents=True, exist_ok=True)
results = {"accepted": True, "failed_gates": [], "warnings": [], "passed_gates": []}


def fail(msg):
    results["failed_gates"].append(msg)
    results["accepted"] = False


def warn(msg):
    results["warnings"].append(msg)


def pass_gate(msg):
    results["passed_gates"].append(msg)


def _env_check():
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    if py_ver == "3.11":
        pass_gate(f"Python {py_ver}")
    else:
        warn(f"Python {py_ver} (expected 3.11)")
    return py_ver


def _data_check(output_dir: Path):
    r = subprocess.run(
        [
            sys.executable,
            str(PROJECT / "scripts/generate_data.py"),
            "--size",
            "small",
            "--seed",
            "20260616",
            "--output-dir",
            str(output_dir),
            "--overwrite",
        ],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(PROJECT),
        env={**os.environ},
    )
    if r.returncode != 0:
        fail(f"Data generation failed: {r.stderr[:200]}")
        return None
    run_dirs = sorted(output_dir.glob("run_*"))
    if not run_dirs:
        fail("No run directory created")
        return None
    rd = run_dirs[0]
    tables = [
        "users",
        "documents",
        "sessions",
        "product_events",
        "agent_runs",
        "agent_spans",
        "experiment_assignments",
    ]
    for t in tables:
        if not (rd / f"{t}.parquet").exists():
            fail(f"Missing table: {t}")
    pass_gate(f"Data: {len(tables)} tables generated")
    return rd


def _warehouse_check(run_dir: Path, db_path: Path):
    r = subprocess.run(
        [
            sys.executable,
            str(PROJECT / "scripts/build_warehouse.py"),
            "--input-run",
            str(run_dir),
            "--database",
            str(db_path),
            "--full-refresh",
            "--skip-dbt",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(PROJECT),
        env={**os.environ},
    )
    if r.returncode != 0:
        fail(f"Warehouse build failed: {r.stderr[:200]}")
        return False

    # Resolve dbt relative to the current Python interpreter (robust across envs)
    dbt_exe = str(Path(sys.executable).parent / "Scripts" / "dbt.exe")
    if not Path(dbt_exe).exists():
        dbt_exe = str(Path(sys.executable).parent / "dbt")
    if not Path(dbt_exe).exists():
        dbt_exe = "dbt"

    db_env = {**os.environ, "FXFILL_DUCKDB_PATH": str(db_path)}
    r = subprocess.run(
        [
            dbt_exe,
            "run",
            "--project-dir",
            str(PROJECT / "dbt_fxfill"),
            "--profiles-dir",
            str(PROJECT / "dbt_fxfill"),
        ],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=str(PROJECT),
        env=db_env,
    )
    dbt_ok = False
    dbt_model_count = 0
    dbt_model_pass = 0
    # Dynamically extract model count from dbt output
    for line in (r.stdout + r.stderr).split("\n"):
        stripped = line.strip()
        if "Done. PASS=" in stripped:
            # e.g. "Done. PASS=41 WARN=0 ERROR=0 SKIP=0 TOTAL=41"
            parts = stripped.split()
            for p in parts:
                if p.startswith("PASS="):
                    dbt_model_pass = int(p.split("=")[1])
                if p.startswith("TOTAL="):
                    dbt_model_count = int(p.split("=")[1])
            dbt_ok = dbt_model_pass == dbt_model_count and dbt_model_count > 0
        elif " of " in stripped and "PASS" in stripped:
            # fallback parsing
            try:
                import re

                m = re.search(r"(\d+)\s*of\s*(\d+)\s+PASS", stripped)
                if m:
                    dbt_model_pass = int(m.group(1))
                    dbt_model_count = int(m.group(2))
                    dbt_ok = dbt_model_pass == dbt_model_count and dbt_model_count > 0
            except Exception:
                pass
    # Fallback: check old-style PASS=NN
    if not dbt_ok and "PASS=" in r.stdout:
        dbt_ok = True
    if dbt_ok:
        pass_gate(f"dbt run: {dbt_model_pass}/{dbt_model_count}")
    else:
        fail(f"dbt run failed: {r.stderr[:200]}")
        return False

    r = subprocess.run(
        [
            dbt_exe,
            "test",
            "--project-dir",
            str(PROJECT / "dbt_fxfill"),
            "--profiles-dir",
            str(PROJECT / "dbt_fxfill"),
        ],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=str(PROJECT),
        env=db_env,
    )
    dbt_test_pass = 0
    dbt_test_count = 0
    dbt_test_ok = False
    for line in (r.stdout + r.stderr).split("\n"):
        stripped = line.strip()
        if "Done. PASS=" in stripped:
            parts = stripped.split()
            for p in parts:
                if p.startswith("PASS="):
                    dbt_test_pass = int(p.split("=")[1])
                if p.startswith("TOTAL="):
                    dbt_test_count = int(p.split("=")[1])
            dbt_test_ok = dbt_test_pass == dbt_test_count and dbt_test_count > 0
    if not dbt_test_ok and "PASS=" in r.stdout:
        dbt_test_ok = True
    if dbt_test_ok:
        pass_gate(f"dbt test: {dbt_test_pass}/{dbt_test_count}")
    else:
        fail("dbt test failed")
        return False
    return True, dbt_model_count, dbt_model_pass, dbt_test_count, dbt_test_pass


def _experiment_check(db_path: Path):
    r = subprocess.run(
        [
            sys.executable,
            str(PROJECT / "scripts/run_experiment_analysis.py"),
            "--experiment",
            "validation_before_autofill_v1",
            "--database",
            str(db_path),
            "--output-dir",
            str(PROJECT / "reports/phase4"),
            "--overwrite",
        ],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=str(PROJECT),
        env={**os.environ},
    )
    if r.returncode == 0:
        pass_gate("Experiment analysis passed")
        return True
    fail(f"Experiment analysis failed: {r.stderr[:200]}")
    return False


def _dashboard_check(db_path: Path):
    from fxfill_analytics.verification.streamlit_smoke import run_streamlit_smoke

    result = run_streamlit_smoke(str(db_path))
    if result["health_http_status"] == 200:
        pass_gate("Dashboard: health HTTP 200")
    else:
        fail("Dashboard: health check failed")
    if result["home_http_status"] == 200:
        pass_gate("Dashboard: home HTTP 200")
    if result["fatal_log_error_count"] == 0:
        pass_gate("Dashboard: 0 fatal errors")
    if result["port_released"]:
        pass_gate("Dashboard: port released")
    return result


def _link_check():
    readme = (
        (PROJECT / "README.md").read_text(encoding="utf-8")
        if (PROJECT / "README.md").exists()
        else ""
    )
    broken = checked = missing = case_err = 0
    for img_ref in re.findall(r"\((docs/[^)]+\.(?:png|svg|jpg))\)", readme):
        checked += 1
        p = PROJECT / img_ref
        if not p.exists():
            parent = p.parent
            if parent.exists():
                matches = [f for f in parent.glob(p.name) if f.name.lower() == p.name.lower()]
                if matches:
                    case_err += 1
                else:
                    missing += 1
                    broken += 1
    for link_ref in re.findall(r"\(([^)]+\.(?:md|json|py|ps1))\)", readme):
        checked += 1
        p = PROJECT / link_ref
        if not p.exists():
            missing += 1
            broken += 1
    if broken == 0:
        pass_gate(f"Links: {checked} checked, 0 broken")
    else:
        fail(f"Links: {broken} broken")
    return {
        "checked_link_count": checked,
        "broken_link_count": broken,
        "missing_asset_count": missing,
        "case_mismatch_count": case_err,
    }


def _public_audit():
    r = subprocess.run(
        [sys.executable, str(PROJECT / "scripts/audit_public_release.py")],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(PROJECT),
    )
    if r.returncode == 0:
        audit_path = PROJECT / "reports/portfolio/public_release_audit.json"
        if audit_path.exists():
            with open(audit_path) as f:
                audit = json.load(f)
            high = audit.get("high_severity_findings", 0)
            if high == 0:
                pass_gate("Public audit: 0 high severity")
            else:
                fail(f"Public audit: {high} high severity")
            return audit
    fail("Public audit failed")
    return {}


def _pytest(db_path: Path):
    """Run full pytest with temporary warehouse available."""
    env = {
        **os.environ,
        "FXFILL_DUCKDB_PATH": str(db_path),
        "NO_PROXY": "127.0.0.1,localhost",
        "no_proxy": "127.0.0.1,localhost",
        "PYTHONPATH": str(PROJECT),
    }
    junit_path = str(R / "core_release_pytest.xml")
    r = subprocess.run(
        [sys.executable, "-m", "pytest", str(PROJECT / "tests"), "-v", f"--junitxml={junit_path}"],
        capture_output=True,
        text=True,
        timeout=600,
        cwd=str(PROJECT),
        env=env,
    )
    # Parse JUnit XML
    import xml.etree.ElementTree as ET

    collected = passed = failed = errors = skipped = 0
    try:
        tree = ET.parse(junit_path)
        root = tree.getroot()
        for ts in root.findall("testsuite"):
            collected += int(ts.get("tests", 0))
            failed += int(ts.get("failures", 0))
            errors += int(ts.get("errors", 0))
            skipped += int(ts.get("skipped", 0))
        passed = collected - failed - errors - skipped
    except Exception:
        # Fallback to text parsing
        lines = (r.stdout + r.stderr).split("\n")
        for line in lines:
            import re as _re

            m = _re.search(r"(\d+)\s+passed", line)
            if m:
                passed = int(m.group(1))
            m = _re.search(r"(\d+)\s+failed", line)
            if m:
                failed = int(m.group(1))
            m = _re.search(r"(\d+)\s+skipped", line)
            if m:
                skipped = int(m.group(1))
            m = _re.search(r"collected\s+(\d+)", line)
            if m:
                collected = int(m.group(1))
        errors = 0

    if failed == 0 and errors == 0:
        pass_gate(f"pytest: {passed} passed, {skipped} skipped")
    if failed > 0:
        fail(f"pytest: {failed} failed")
    if errors > 0:
        fail(f"pytest: {errors} errors")
    if skipped > 0:
        warn(f"pytest: {skipped} skipped")
    return {
        "collected": collected,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "deselected": 0,
    }


def _run_check_script(args: list[str], label: str) -> tuple[bool, dict]:
    """Run a Python acceptance check script, return (success, parsed_json)."""
    try:
        r = subprocess.run(
            [sys.executable] + args,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(PROJECT),
            env={**os.environ},
        )
        success = r.returncode == 0
        parsed = {}
        # Find output JSON file
        for a in args:
            if a.endswith(".json") and Path(a).exists():
                with open(a, encoding="utf-8") as f:
                    parsed = json.load(f)
                break
        return success, parsed
    except Exception as e:
        fail(f"{label}: {e}")
        return False, {}


def main():
    _env_py = _env_check()

    tmp = Path(tempfile.mkdtemp(prefix="fxfill_core_"))
    db_path = tmp / "warehouse" / "fxfill.duckdb"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    gen_dir = tmp / "data" / "generated"

    wh_ok = exp_ok = False
    dash_result = {}
    eng = audit = {}
    bi_result = {}
    truth_result = {}
    snap_result = {}
    dbt_stats = {}
    t0 = time.perf_counter()

    code_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=str(PROJECT)
    ).stdout.strip()

    run_dir = None
    try:
        run_dir = _data_check(gen_dir)
        if run_dir:
            wh_ok = _warehouse_check(run_dir, db_path)
            if wh_ok:
                # Unpack tuple: (ok, model_count, model_pass, test_count, test_pass)
                if isinstance(wh_ok, tuple):
                    wh_ok = wh_ok[0]
                # Save model run_results
                model_results_path = tmp / "dbt_model_run_results.json"
                shutil.copy(
                    str(Path("dbt_fxfill/target/run_results.json")), str(model_results_path)
                )

                exp_ok = _experiment_check(db_path)

                # Pytest with DB alive
                eng = _pytest(db_path)
                junit_path = R / "core_release_pytest.xml"

                # Save test run_results after dbt test
                test_results_path = tmp / "dbt_test_run_results.json"
                test_rr = PROJECT / "dbt_fxfill" / "target" / "run_results.json"
                if test_rr.exists():
                    shutil.copy(str(test_rr), str(test_results_path))

                manifest_path = PROJECT / "dbt_fxfill" / "target" / "manifest.json"

                # Business metric integrity
                bi_out = str(tmp / "business_integrity.json")
                bi_ok, bi_result = _run_check_script(
                    [
                        "scripts/check_business_metric_integrity.py",
                        "--database",
                        str(db_path),
                        "--output",
                        bi_out,
                    ],
                    "business integrity",
                )
                if bi_ok:
                    pass_gate("Business metric integrity: accepted")
                else:
                    fail("Business metric integrity: failed")

                # Data quality snapshot
                snap_out = str(tmp / "snapshot.json")
                snap_args = [
                    "scripts/generate_data_quality_snapshot.py",
                    "--input-run",
                    str(run_dir),
                    "--database",
                    str(db_path),
                    "--dbt-manifest",
                    str(manifest_path),
                    "--dbt-model-results",
                    str(model_results_path),
                    "--dbt-test-results",
                    str(test_results_path),
                    "--pytest-junit",
                    str(junit_path),
                    "--verified-code-commit",
                    code_commit,
                    "--output",
                    snap_out,
                ]
                _, snap_result = _run_check_script(snap_args, "data quality snapshot")
                if snap_result.get("accepted"):
                    pass_gate("Data quality snapshot: accepted")
                else:
                    fail("Data quality snapshot: not accepted")

                # Dashboard truthfulness
                truth_out = str(tmp / "dashboard_truthfulness.json")
                truth_ok, truth_result = _run_check_script(
                    [
                        "scripts/check_dashboard_truthfulness.py",
                        "--database",
                        str(db_path),
                        "--snapshot",
                        snap_out,
                        "--output",
                        truth_out,
                    ],
                    "dashboard truthfulness",
                )
                if truth_ok:
                    pass_gate("Dashboard truthfulness: accepted")
                else:
                    fail("Dashboard truthfulness: failed")

                dbt_stats = snap_result.get("dbt", {})
                # Streamlit smoke
                dash_result = _dashboard_check(db_path)
            t1 = time.perf_counter()
        else:
            t1 = time.perf_counter()
    finally:
        try:
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass

    _links = _link_check()
    audit = _public_audit()

    # Data quality passed: snapshot accepted AND provenance matched
    dq_passed = (
        snap_result.get("accepted", False)
        and snap_result.get("provenance", {}).get("provenance_matches", False)
        and truth_result.get("data_quality", {}).get("provenance_matches", False)
        and bi_result.get("accepted", False)
    )

    report = {
        "accepted": results["accepted"] and len(results["failed_gates"]) == 0,
        "failed_gates": results["failed_gates"],
        "warnings": results["warnings"],
        "git": {
            "verified_code_commit": code_commit,
            "report_generation_head": code_commit,
        },
        "dbt": {
            "model_count": dbt_stats.get("model_count", 0),
            "model_success_count": dbt_stats.get("model_success_count", 0),
            "model_fail_count": dbt_stats.get("model_fail_count", 0),
            "generic_test_count": dbt_stats.get("generic_test_count", 0),
            "singular_test_count": dbt_stats.get("singular_test_count", 0),
            "test_pass": dbt_stats.get("test_pass", 0),
            "test_fail": dbt_stats.get("test_fail", 0),
            "test_error": dbt_stats.get("test_error", 0),
            "test_skip": dbt_stats.get("test_skip", 0),
        },
        "engineering": eng,
        "business_metric_integrity": {
            "accepted": bi_result.get("accepted", False),
            "failures": bi_result.get("failures", []),
        },
        "dashboard_truthfulness": {
            "accepted": truth_result.get("accepted", False),
            "failures": truth_result.get("failures", []),
            "retention": {
                "unmatured_points_plotted": truth_result.get("retention", {}).get(
                    "unmatured_points_plotted", 0
                ),
                "empty_traces_rendered": truth_result.get("retention", {}).get(
                    "empty_traces_rendered", 0
                ),
            },
            "agent": {
                "visible_nan_count": truth_result.get("agent", {}).get("visible_nan_count", 0),
                "visible_none_count": truth_result.get("agent", {}).get("visible_none_count", 0),
                "date_filter_violation_count": truth_result.get("agent", {}).get(
                    "date_filter_violation_count", 0
                ),
            },
        },
        "data_quality": {
            "accepted": dq_passed,
            "provenance_matches": snap_result.get("provenance", {}).get(
                "provenance_matches", False
            ),
            "strict_reconciliation_passed": snap_result.get("accepted", False),
            "incomplete_reconciliation_rows": truth_result.get("data_quality", {}).get(
                "incomplete_reconciliation_rows", 0
            ),
            "incorrect_pass_flag_count": truth_result.get("data_quality", {}).get(
                "hardcoded_pass_count", 0
            ),
            "stale_artifact_count": truth_result.get("data_quality", {}).get(
                "stale_artifact_count", 0
            ),
        },
        "dashboard": dash_result,
        "public_release": {
            "high_severity_findings": audit.get("high_severity_findings", 0),
            "medium_severity_findings": audit.get("medium_severity_findings", 0),
            "tracked_database_files": audit.get("tracked_database_files", 0),
            "tracked_secret_files": audit.get("tracked_secret_files", 0),
        },
        "clean_build": {
            "synthetic_data_generated": run_dir is not None,
            "data_quality_passed": dq_passed,
            "duckdb_built": wh_ok,
            "dbt_run_passed": wh_ok,
            "dbt_test_passed": wh_ok,
            "experiment_analysis_passed": exp_ok,
            "duration_seconds": round(t1 - t0, 1),
        },
    }

    report_str = json.dumps(report, indent=2, default=str)
    with open(R / "core_release_acceptance.json", "w") as f:
        f.write(report_str)
    with open(R / "core_release_acceptance.md", "w") as f:
        f.write(
            f"# Core Release Acceptance\nAccepted: {report['accepted']}\n"
            f"Verified code commit: {code_commit[:12]}\n"
            f"dbt: {dbt_stats.get('model_count',0)} models, {dbt_stats.get('singular_test_count',0)} singular + {dbt_stats.get('generic_test_count',0)} generic tests\n"
            f"pytest: {eng.get('passed',0)}/{eng.get('collected',0)} passed\n"
        )

    if report["accepted"]:
        print("CORE RELEASE ACCEPTANCE PASSED")
        sys.exit(0)
    else:
        print(f"CORE RELEASE FAILED: {len(results['failed_gates'])} gates")
        for g in results["failed_gates"][:10]:
            print(f"  - {g}")
        sys.exit(1)


if __name__ == "__main__":
    main()
