"""Real Streamlit startup test with health endpoint verification."""
import json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path
import pytest

PROJECT = Path(__file__).resolve().parent.parent.parent
DB_PATH = os.environ.get("FXFILL_DUCKDB_PATH", str((PROJECT / "warehouse" / "fxfill.duckdb").resolve()))


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _poll_health(port: int, proc, max_wait: int = 60, interval: float = 0.5) -> dict:
    """Poll Streamlit endpoints. Streamlit returns 502 while loading; 200 when ready."""
    import urllib.request
    import urllib.error
    deadline = time.time() + max_wait
    attempts = 0
    health_ok = False
    home_ok = False
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        attempts += 1
        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=1)
            if resp.status == 200:
                health_ok = True
                try:
                    resp2 = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2)
                    if resp2.status == 200 and len(resp2.read()) > 100:
                        home_ok = True
                        break
                except Exception:
                    pass
        except urllib.error.HTTPError as e:
            if e.code == 502:  # Still loading, retry
                pass
        except Exception:
            pass
        time.sleep(interval)
    return {"attempts": attempts, "health_ok": health_ok, "home_ok": home_ok,
            "elapsed": time.time() - (time.time() + interval - deadline + max_wait) + interval}


def test_real_streamlit_startup():
    """Start Streamlit subprocess, verify health + home endpoints, check logs."""
    if not Path(DB_PATH).exists():
        pytest.skip(f"Database not found: {DB_PATH}")

    port = _find_free_port()
    cmd = [sys.executable, "-m", "streamlit", "run", str(PROJECT / "dashboard" / "Home.py"),
           "--server.headless=true", f"--server.port={port}", "--server.address=127.0.0.1",
           "--browser.gatherUsageStats=false"]
    env = {**os.environ, "FXFILL_DUCKDB_PATH": DB_PATH,
           "PYTHONPATH": str(PROJECT), "PYTHONNOUSERSITE": "1",
           "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost"}

    log_fd, log_path = tempfile.mkstemp(suffix=".log", prefix="streamlit_test_")
    os.close(log_fd)
    log_file = open(log_path, "w", encoding="utf-8")

    t0 = time.time()
    proc = subprocess.Popen(cmd, cwd=str(PROJECT), stdout=log_file, stderr=subprocess.STDOUT, env=env)
    time.sleep(3)  # Wait for Streamlit to start

    # Check for instant crash
    if proc.poll() is not None:
        log_file.close()
        log_text = Path(log_path).read_text(encoding="utf-8", errors="replace")
        fatal_keywords = ["Traceback", "ImportError", "ModuleNotFoundError", "StreamlitAPIException",
                          "Catalog Error", "Address already in use"]
        found = [k for k in fatal_keywords if k in log_text]
        pytest.fail(f"Streamlit crashed (rc={proc.returncode}). Fatal: {found}\nFirst 800 chars: {log_text[:800]}")

    # Poll for health endpoint
    diag = _poll_health(port, proc, max_wait=90)

    # Terminate
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    log_file.close()

    elapsed = time.time() - t0
    log_text = Path(log_path).read_text(encoding="utf-8", errors="replace")
    fatal_keywords = ["Traceback", "ImportError", "ModuleNotFoundError", "StreamlitAPIException",
                      "Catalog Error", "Address already in use"]
    fatal_found = [k for k in fatal_keywords if k in log_text]

    # Port released check
    port_free = True
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", port))
        s.close()
    except OSError:
        port_free = False

    # Write diagnostic
    diagnostic = {
        "command": " ".join(cmd), "working_directory": str(PROJECT),
        "python_executable": sys.executable, "duckdb_path": DB_PATH,
        "selected_port": port, "process_return_code": proc.returncode,
        "health_attempts": diag["attempts"], "health_ok": diag["health_ok"],
        "home_ok": diag["home_ok"], "timeout_duration": diag["elapsed"],
        "fatal_log_errors": fatal_found, "fatal_error_count": len(fatal_found),
        "port_released": port_free, "process_terminated_cleanly": proc.returncode is not None,
        "startup_passed": diag["health_ok"] and diag["home_ok"] and len(fatal_found) == 0,
        "startup_duration_seconds": round(elapsed, 1),
    }
    reports_dir = PROJECT / "reports"
    reports_dir.mkdir(exist_ok=True)
    with open(reports_dir / "phase3_streamlit_startup_diagnostic.json", "w") as f:
        json.dump(diagnostic, f, indent=2)
    import shutil
    shutil.move(log_path, str(reports_dir / "phase3_streamlit_startup_diagnostic.log"))

    assert diag["health_ok"], f"Health endpoint not reachable on port {port}. Log: {log_path}"
    assert diag["home_ok"], f"Home page not reachable on port {port}"
    assert len(fatal_found) == 0, f"Fatal log errors: {fatal_found}"
    assert port_free, f"Port {port} not released"
    assert proc.returncode is not None, "Process did not terminate"
