"""Shared Streamlit smoke test — used by verifier and pytest."""

import http.client
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def run_streamlit_smoke(db_path: str, timeout_seconds: int = 120) -> dict:
    """Start Streamlit, verify health + home endpoints, return structured result.

    Uses ``http.client`` for direct HTTP communication (avoids proxy
    interference that can affect ``urllib.request.urlopen`` on Windows).
    """
    # ── find a free port ──────────────────────────────────────────────────
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    log_fd, log_path = tempfile.mkstemp(suffix=".log", prefix="streamlit_smoke_")
    os.close(log_fd)
    log_file = open(log_path, "w", encoding="utf-8")

    project_root = Path(__file__).resolve().parent.parent.parent.parent

    env = {
        **os.environ,
        "FXFILL_DUCKDB_PATH": db_path,
        "NO_PROXY": "127.0.0.1,localhost",
        "no_proxy": "127.0.0.1,localhost",
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": str(project_root),
    }

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(project_root / "dashboard" / "Home.py"),
        "--server.headless=true",
        f"--server.port={port}",
        "--server.address=127.0.0.1",
        "--browser.gatherUsageStats=false",
    ]

    proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, env=env)
    time.sleep(5)

    # ── early-exit if the process crashed on startup ──────────────────────
    if proc.poll() is not None:
        log_file.close()
        log_text = Path(log_path).read_text(encoding="utf-8", errors="replace")
        fatal_keywords = [
            "Traceback",
            "ImportError",
            "ModuleNotFoundError",
            "StreamlitAPIException",
            "Catalog Error",
            "Address already in use",
        ]
        found = [k for k in fatal_keywords if k in log_text]
        return {
            "health_http_status": 0,
            "home_http_status": 0,
            "fatal_log_error_count": len(found),
            "process_terminated_cleanly": True,
            "port_released": True,
            "startup_passed": False,
            "error": f"RC={proc.returncode}",
            "log_path": log_path,
        }

    health_ok = home_ok = False

    def _http_get(path: str, timeout: int = 60) -> int | None:
        """Return HTTP status code for *path*, or None on connection error."""
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
        try:
            conn.request("GET", path)
            resp = conn.getresponse()
            # Read body to completion so connection can be reused
            resp.read()
            return resp.status
        except (ConnectionRefusedError, ConnectionResetError, OSError):
            return None
        finally:
            conn.close()

    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        if proc.poll() is not None:
            break

        # Check home first — triggers script execution in headless mode
        if not home_ok:
            status = _http_get("/", timeout=60)
            if status == 200:
                home_ok = True
            elif status is None:
                # Server not yet accepting connections
                time.sleep(2)
                continue

        # Check health endpoint
        if not health_ok:
            status = _http_get("/_stcore/health", timeout=5)
            if status == 200:
                health_ok = True

        if health_ok and home_ok:
            break

        time.sleep(2)

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    log_file.close()

    port_free = True
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", port))
        s.close()
    except OSError:
        port_free = False

    log_text = Path(log_path).read_text(encoding="utf-8", errors="replace")
    fatal_keywords = [
        "Traceback",
        "ImportError",
        "ModuleNotFoundError",
        "StreamlitAPIException",
        "Catalog Error",
        "Address already in use",
    ]
    fatal_found = [k for k in fatal_keywords if k in log_text]

    return {
        "health_http_status": 200 if health_ok else 0,
        "home_http_status": 200 if home_ok else 0,
        "fatal_log_error_count": len(fatal_found),
        "process_terminated_cleanly": proc.returncode is not None,
        "port_released": port_free,
        "startup_passed": health_ok and home_ok and len(fatal_found) == 0,
    }
