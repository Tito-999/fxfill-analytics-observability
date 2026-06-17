"""Shared Streamlit smoke test — used by verifier and pytest."""
import json, os, shutil, socket, subprocess, sys, tempfile, time
from pathlib import Path


def run_streamlit_smoke(db_path: str, timeout: int = 60) -> dict:
    """Start Streamlit, verify health+home, return structured result."""
    port = None
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    log_fd, log_path = tempfile.mkstemp(suffix=".log", prefix="streamlit_smoke_")
    os.close(log_fd)
    log_file = open(log_path, "w", encoding="utf-8")

    env = {**os.environ,
           "FXFILL_DUCKDB_PATH": db_path,
           "NO_PROXY": "127.0.0.1,localhost",
           "no_proxy": "127.0.0.1,localhost",
           "PYTHONNOUSERSITE": "1",
           "PYTHONPATH": str(Path(__file__).resolve().parent.parent.parent.parent)}

    cmd = [sys.executable, "-m", "streamlit", "run",
           str(Path(__file__).resolve().parent.parent.parent.parent / "dashboard" / "Home.py"),
           "--server.headless=true", f"--server.port={port}",
           "--server.address=127.0.0.1", "--browser.gatherUsageStats=false"]

    proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, env=env)
    time.sleep(3)

    if proc.poll() is not None:
        log_file.close()
        log_text = Path(log_path).read_text(encoding="utf-8", errors="replace")
        fatal_keywords = ["Traceback", "ImportError", "ModuleNotFoundError",
                          "StreamlitAPIException", "Catalog Error", "Address already in use"]
        found = [k for k in fatal_keywords if k in log_text]
        return {"health_http_status": 0, "home_http_status": 0,
                "fatal_log_error_count": len(found),
                "process_terminated_cleanly": True, "port_released": True,
                "startup_passed": False, "error": f"RC={proc.returncode}",
                "log_path": log_path}

    health_ok = home_ok = False
    import urllib.request, urllib.error
    for _ in range(timeout):
        if proc.poll() is not None:
            break
        try:
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
    log_file.close()

    port_free = True
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", port))
        s.close()
    except OSError:
        port_free = False

    log_text = Path(log_path).read_text(encoding="utf-8", errors="replace")
    fatal_keywords = ["Traceback", "ImportError", "ModuleNotFoundError",
                      "StreamlitAPIException", "Catalog Error", "Address already in use"]
    fatal_found = [k for k in fatal_keywords if k in log_text]

    return {
        "health_http_status": 200 if health_ok else 0,
        "home_http_status": 200 if home_ok else 0,
        "fatal_log_error_count": len(fatal_found),
        "process_terminated_cleanly": proc.returncode is not None,
        "port_released": port_free,
        "startup_passed": health_ok and home_ok and len(fatal_found) == 0,
    }
