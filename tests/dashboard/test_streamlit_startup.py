"""Real Streamlit startup smoke test with health endpoint verification."""
import subprocess, sys, time, socket, os
from pathlib import Path
import pytest
import urllib.request
import urllib.error

PROJECT = Path(__file__).resolve().parent.parent.parent
DB_PATH = str((PROJECT / "warehouse" / "fxfill.duckdb").resolve())


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_health(port: int, timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=2)
            if resp.status == 200:
                return True
        except Exception:
            pass
        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2)
            if resp.status == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def test_real_streamlit_startup():
    """Start Streamlit, verify health endpoint, check logs for fatal errors."""
    if not Path(DB_PATH).exists():
        pytest.skip("DuckDB not built")

    port = _find_free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(PROJECT / "dashboard" / "Home.py"),
         "--server.headless", "true", "--server.port", str(port),
         "--browser.gatherUsageStats", "false"],
        cwd=str(PROJECT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "FXFILL_DUCKDB_PATH": DB_PATH, "PYTHONNOUSERSITE": "1"},
    )

    health_ok = _wait_for_health(port)
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    stderr_text = (proc.stderr.read() if proc.stderr else b"").decode("utf-8", errors="replace")
    fatal_patterns = ["Traceback", "ImportError", "ModuleNotFoundError",
                      "StreamlitAPIException", "Catalog Error", "Address already in use"]
    fatal_found = [p for p in fatal_patterns if p in stderr_text]

    # Check port released
    port_free = True
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", port))
        s.close()
    except OSError:
        port_free = False

    assert health_ok, f"Health endpoint not reachable on port {port}"
    assert len(fatal_found) == 0, f"Fatal log errors: {fatal_found}"
    assert port_free, f"Port {port} not released"
    assert proc.returncode is not None or proc.poll() is not None, "Process did not terminate"
