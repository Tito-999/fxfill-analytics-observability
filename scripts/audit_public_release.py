"""Audit Git-tracked files for secrets, private paths, and sensitive data."""
import json, subprocess, sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
R = PROJECT / "reports" / "portfolio"
R.mkdir(parents=True, exist_ok=True)

result = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=str(PROJECT))
files = result.stdout.strip().split("\n")

# Detection patterns
HIGH_SEVERITY = [
    (r"(?:sk-or-|sk-proj-|sk-ant-|sk-svcacct-)", "OpenAI/Anthropic API key prefix"),
    (r"api_key\s*=\s*['\"]\w{20,}['\"]", "API key assignment"),
    (r"BEGIN\s+(RSA|DSA|EC|OPENSSH|PRIVATE\s+KEY)", "Private key"),
    (r"password\s*=\s*['\"]\S{8,}['\"]", "Hardcoded password"),
]
MEDIUM_SEVERITY = [
    (r"C:\\Users\\", "Windows user path (ignore if in documentation)"),
    (r"F:\\RAG\\", "Project drive root (this project's path)"),
    (r"/home/", "Linux home path"),
]
# Allowlist files that legitimately contain path references
ALLOWLIST_PATHS = {"docs/decisions/001-verified-dependency-versions.md",
                    "reports/phase2_warehouse_manifest.json",
                    "reports/phase3_streamlit_startup_diagnostic.json",
                    "scripts/run_dashboard.ps1",
                    "tests/integration/test_phase2_audit.py"}
ALLOWLIST_API = {"dbt_fxfill/models/intermediate/int_task_outcomes.sql",
                  "tests/unit/test_smoke.py"}
TRACKED_LARGE = [".duckdb", ".parquet"]

findings = {"high_severity": [], "medium_severity": [], "tracked_large_files": []}

SKIP_SELF = {"scripts/audit_public_release.py", "reports/portfolio/public_release_audit.json"}
for f in files:
    if f in SKIP_SELF: continue
    path = PROJECT / f
    if not path.exists() or path.stat().st_size > 50_000_000:
        continue

    # Check for large tracked files
    if any(f.endswith(ext) for ext in TRACKED_LARGE):
        findings["tracked_large_files"].append(f)

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue

    if f not in ALLOWLIST_API:
        for pattern, desc in HIGH_SEVERITY:
            import re
            if re.search(pattern, content):
                findings["high_severity"].append({"file": f, "pattern": pattern, "description": desc})

    if f not in ALLOWLIST_PATHS:
        for pattern, desc in MEDIUM_SEVERITY:
            import re
            if re.search(pattern, content):
                findings["medium_severity"].append({"file": f, "pattern": pattern, "description": desc})

    # Check for .env
    if f.endswith(".env") and f != ".env.example":
        findings["high_severity"].append({"file": f, "description": "Environment file"})

# Check for tracked database files
for f in files:
    if ".duckdb" in f:
        findings["high_severity"].append({"file": f, "description": "Tracked DuckDB file"})

summary = {
    "high_severity_findings": len(findings["high_severity"]),
    "medium_severity_findings": len(findings["medium_severity"]),
    "tracked_database_files": sum(1 for f in files if ".duckdb" in f),
    "tracked_medium_data_files": sum(1 for f in files if "medium_in" in f.lower()),
    "tracked_secret_files": sum(1 for f in files if f.endswith(".env")),
    "absolute_private_paths": len(findings["medium_severity"]),
    "passed": len(findings["high_severity"]) == 0,
    "findings": findings,
}
with open(R / "public_release_audit.json", "w") as f:
    json.dump(summary, f, indent=2)
print(f"High severity: {summary['high_severity_findings']}, Medium: {summary['medium_severity_findings']}")
if summary["high_severity_findings"] > 0:
    print("PUBLIC RELEASE BLOCKED")
    sys.exit(1)
print("Public release audit passed")
