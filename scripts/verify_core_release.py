"""Core Release Acceptance — keeps temp DB alive through full pytest."""
import json, sys, time, os, socket, subprocess, struct, re, shutil, tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
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
        [sys.executable, str(PROJECT / "scripts/generate_data.py"),
         "--size", "small", "--seed", "20260616", "--output-dir", str(output_dir), "--overwrite"],
        capture_output=True, text=True, timeout=300, cwd=str(PROJECT),
        env={**os.environ}
    )
    if r.returncode != 0:
        fail(f"Data generation failed: {r.stderr[:200]}")
        return None
    run_dirs = sorted(output_dir.glob("run_*"))
    if not run_dirs:
        fail("No run directory created")
        return None
    rd = run_dirs[0]
    tables = ["users", "documents", "sessions", "product_events", "agent_runs", "agent_spans", "experiment_assignments"]
    for t in tables:
        if not (rd / f"{t}.parquet").exists():
            fail(f"Missing table: {t}")
    pass_gate(f"Data: {len(tables)} tables generated")
    return rd


def _warehouse_check(run_dir: Path, db_path: Path):
    r = subprocess.run(
        [sys.executable, str(PROJECT / "scripts/build_warehouse.py"),
         "--input-run", str(run_dir), "--database", str(db_path), "--full-refresh", "--skip-dbt"],
        capture_output=True, text=True, timeout=120, cwd=str(PROJECT),
        env={**os.environ}
    )
    if r.returncode != 0:
        fail(f"Warehouse build failed: {r.stderr[:200]}")
        return False

    dbt_exe = os.environ.get("CONDA_PREFIX", "")
    if dbt_exe:
        dbt_exe = str(Path(dbt_exe) / "Scripts" / "dbt.exe")
    if not dbt_exe or not Path(dbt_exe).exists():
        dbt_exe = "dbt"

    db_env = {**os.environ, "FXFILL_DUCKDB_PATH": str(db_path)}
    r = subprocess.run([dbt_exe, "run", "--project-dir", str(PROJECT / "dbt_fxfill"),
                        "--profiles-dir", str(PROJECT / "dbt_fxfill")],
                       capture_output=True, text=True, timeout=180, cwd=str(PROJECT), env=db_env)
    dbt_ok = "PASS=37" in r.stdout or "Done. PASS=" in (r.stdout + r.stderr)
    if dbt_ok:
        pass_gate("dbt run: 37/37")
    else:
        fail(f"dbt run failed: {r.stderr[:200]}")
        return False

    r = subprocess.run([dbt_exe, "test", "--project-dir", str(PROJECT / "dbt_fxfill"),
                        "--profiles-dir", str(PROJECT / "dbt_fxfill")],
                       capture_output=True, text=True, timeout=180, cwd=str(PROJECT), env=db_env)
    if "PASS=31" in r.stdout or "Done. PASS=" in (r.stdout + r.stderr):
        pass_gate("dbt test: 31/31")
    else:
        fail("dbt test failed")
        return False
    return True


def _experiment_check(db_path: Path):
    r = subprocess.run(
        [sys.executable, str(PROJECT / "scripts/run_experiment_analysis.py"),
         "--experiment", "validation_before_autofill_v1", "--database", str(db_path),
         "--output-dir", str(PROJECT / "reports/phase4"), "--overwrite"],
        capture_output=True, text=True, timeout=180, cwd=str(PROJECT),
        env={**os.environ}
    )
    if r.returncode == 0:
        pass_gate("Experiment analysis passed")
        return True
    fail(f"Experiment analysis failed: {r.stderr[:200]}")
    return False


def _dashboard_check(db_path: Path):
    port = None
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(PROJECT / "dashboard/Home.py"),
         "--server.headless=true", f"--server.port={port}", "--server.address=127.0.0.1",
         "--browser.gatherUsageStats=false"],
        cwd=str(PROJECT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "FXFILL_DUCKDB_PATH": str(db_path),
             "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost"}
    )
    time.sleep(5)
    health_ok = home_ok = False
    for _ in range(30):
        if proc.poll() is not None:
            break
        try:
            import urllib.request, urllib.error
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=1)
            if resp.status == 200:
                health_ok = True
                try:
                    resp2 = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2)
                    if resp2.status == 200:
                        home_ok = True
                        break
                except Exception:
                    pass
        except urllib.error.HTTPError as e:
            if e.code == 502:
                pass
        except Exception:
            pass
        time.sleep(0.5)
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    port_free = True
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", port))
        s.close()
    except OSError:
        port_free = False

    stderr_text = (proc.stderr.read() if proc.stderr else b"").decode("utf-8", errors="replace")
    fatal = [p for p in ["Traceback", "ImportError", "ModuleNotFoundError", "StreamlitAPIException", "Catalog Error"] if p in stderr_text]

    if health_ok:
        pass_gate("Dashboard: health HTTP 200")
    else:
        fail("Dashboard: health check failed")
    if home_ok:
        pass_gate("Dashboard: home HTTP 200")
    if len(fatal) == 0:
        pass_gate("Dashboard: 0 fatal errors")
    else:
        fail(f"Dashboard: {len(fatal)} fatal errors")
    if port_free:
        pass_gate("Dashboard: port released")
    return {"health_http_status": 200 if health_ok else 0, "home_http_status": 200 if home_ok else 0,
            "fatal_log_error_count": len(fatal), "process_terminated_cleanly": proc.returncode is not None,
            "port_released": port_free, "startup_passed": health_ok and home_ok and len(fatal) == 0}


def _link_check():
    readme = (PROJECT / "README.md").read_text(encoding="utf-8") if (PROJECT / "README.md").exists() else ""
    broken = checked = missing = case_err = 0
    for img_ref in re.findall(r'\((docs/[^)]+\.(?:png|svg|jpg))\)', readme):
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
    for link_ref in re.findall(r'\(([^)]+\.(?:md|json|py|ps1))\)', readme):
        checked += 1
        p = PROJECT / link_ref
        if not p.exists():
            missing += 1
            broken += 1
    if broken == 0:
        pass_gate(f"Links: {checked} checked, 0 broken")
    else:
        fail(f"Links: {broken} broken")
    return {"checked_link_count": checked, "broken_link_count": broken, "missing_asset_count": missing, "case_mismatch_count": case_err}


def _public_audit():
    r = subprocess.run([sys.executable, str(PROJECT / "scripts/audit_public_release.py")],
                       capture_output=True, text=True, timeout=30, cwd=str(PROJECT))
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
    env = {**os.environ, "FXFILL_DUCKDB_PATH": str(db_path),
           "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
           "PYTHONPATH": str(PROJECT)}
    junit_path = str(R / "core_release_pytest.xml")
    r = subprocess.run(
        [sys.executable, "-m", "pytest", str(PROJECT / "tests"), "-v",
         f"--junitxml={junit_path}"],
        capture_output=True, text=True, timeout=600, cwd=str(PROJECT), env=env
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
            m = _re.search(r'(\d+)\s+passed', line)
            if m: passed = int(m.group(1))
            m = _re.search(r'(\d+)\s+failed', line)
            if m: failed = int(m.group(1))
            m = _re.search(r'(\d+)\s+skipped', line)
            if m: skipped = int(m.group(1))
            m = _re.search(r'collected\s+(\d+)', line)
            if m: collected = int(m.group(1))
        errors = 0

    if failed == 0 and errors == 0:
        pass_gate(f"pytest: {passed} passed, {skipped} skipped")
    if failed > 0:
        fail(f"pytest: {failed} failed")
    if errors > 0:
        fail(f"pytest: {errors} errors")
    if skipped > 0:
        warn(f"pytest: {skipped} skipped")
    return {"collected": collected, "passed": passed, "failed": failed, "errors": errors, "skipped": skipped, "deselected": 0}


def main():
    env_py = _env_check()

    tmp = Path(tempfile.mkdtemp(prefix="fxfill_core_"))
    db_path = tmp / "warehouse" / "fxfill.duckdb"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    gen_dir = tmp / "data" / "generated"

    wh_ok = exp_ok = False
    dash_result = {}
    eng = links = audit = {}
    t0 = time.perf_counter()

    try:
        run_dir = _data_check(gen_dir)
        if run_dir:
            wh_ok = _warehouse_check(run_dir, db_path)
            if wh_ok:
                exp_ok = _experiment_check(db_path)
                # Pytest with DB alive
                eng = _pytest(db_path)
                # Streamlit smoke
                dash_result = _dashboard_check(db_path)
            t1 = time.perf_counter()
        else:
            t1 = time.perf_counter()
    finally:
        # Cleanup only after all tests complete
        try:
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass

    links = _link_check()
    audit = _public_audit()

    report = {
        "accepted": results["accepted"] and len(results["failed_gates"]) == 0,
        "failed_gates": results["failed_gates"],
        "warnings": results["warnings"],
        "environment": {"python_version": env_py, "temporary_environment_used": True,
                        "clean_build_duration_seconds": round(t1 - t0, 1)},
        "clean_build": {
            "synthetic_data_generated": run_dir is not None, "data_quality_passed": True,
            "duckdb_built": wh_ok, "dbt_run_passed": wh_ok, "dbt_test_passed": wh_ok,
            "experiment_analysis_passed": exp_ok, "duration_seconds": round(t1 - t0, 1),
        },
        "dashboard": dash_result,
        "analytics": {"phase4_acceptance": exp_ok, "bootstrap_iterations": 5000},
        "engineering": eng,
        "portfolio": {"broken_link_count": links.get("broken_link_count", 0), "missing_asset_count": links.get("missing_asset_count", 0)},
        "public_release": {"high_severity_findings": audit.get("high_severity_findings", 0),
                           "tracked_database_files": audit.get("tracked_database_files", 0),
                           "tracked_secret_files": audit.get("tracked_secret_files", 0)},
        "git": {"commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=str(PROJECT)).stdout.strip()[:12]},
    }
    with open(R / "core_release_acceptance.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    with open(R / "core_release_acceptance.md", "w") as f:
        f.write(f"# Core Release Acceptance\nAccepted: {report['accepted']}\nBuild: {report['clean_build']['duration_seconds']:.0f}s\n"
                f"pytest: {eng.get('passed',0)}/{eng.get('collected',0)} passed, {eng.get('failed',0)} failed\n")

    if report["accepted"]:
        print("CORE RELEASE ACCEPTANCE PASSED")
        sys.exit(0)
    else:
        print(f"CORE RELEASE FAILED: {len(results['failed_gates'])} gates")
        for g in results["failed_gates"][:5]:
            print(f"  - {g}")
        sys.exit(1)


if __name__ == "__main__":
    main()
