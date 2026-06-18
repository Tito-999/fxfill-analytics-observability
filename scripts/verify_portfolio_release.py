"""Portfolio Release Acceptance Verifier — active facts, assets, and evidence."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
R = PROJECT / "reports" / "portfolio"
R.mkdir(parents=True, exist_ok=True)

REQUIRED_FILES = [
    "README.md",
    "docs/portfolio/architecture.mmd",
    "docs/portfolio/architecture.svg",
    "docs/portfolio/architecture.png",
    "docs/portfolio/data_flow.mmd",
    "docs/portfolio/data_flow.svg",
    "docs/portfolio/data_flow.png",
    "docs/portfolio/experiment_flow.mmd",
    "docs/portfolio/experiment_flow.svg",
    "docs/portfolio/experiment_flow.png",
    "docs/portfolio/dashboard_contact_sheet.png",
    "docs/portfolio/screenshot_manifest.json",
    "docs/portfolio/recruiter_quickstart.md",
    "docs/portfolio/technical_deep_dive.md",
    "docs/portfolio/resume_bullets.md",
    "scripts/setup_portfolio.ps1",
    "scripts/setup_portfolio.sh",
    "scripts/run_portfolio_demo.ps1",
    "scripts/run_portfolio_demo.sh",
    "scripts/audit_public_release.py",
    "scripts/verify_portfolio_release.py",
]
SCREENSHOTS = [
    "home.png",
    "executive_overview.png",
    "funnel_retention.png",
    "feature_adoption.png",
    "agent_observability.png",
    "ab_test.png",
    "root_cause.png",
    "data_quality.png",
]

results = {
    "accepted": True,
    "failed_gates": [],
    "passed_gates": [],
    "warnings": [],
    "stale_fact_findings": [],
    "schema_version": "3.0.0",
}

# ── CLI ──
parser = argparse.ArgumentParser()
parser.add_argument(
    "--allow-missing-current-core-report",
    action="store_true",
    help="Do not fail when current core release acceptance report is absent.",
)
args = parser.parse_args()

STALE_PATTERNS = [
    (r"(?<!\")\b37[ -]+dbt[ -]*models?(?!\")", "37 dbt models"),
    (r"(?<!\")\b37[ -]+SQL[ -]*models?(?!\")", "37 SQL models"),
    (r"\b12[ -]+intermediate[ -]*(?:views?|models?)\b", "12 intermediate"),
    (r"[Ii]ntermediate\s*\(12\)", "Intermediate (12)"),
    (r"\b18[ -]+analytics[ -]+marts?\b", "18 analytics marts"),
    (r"\b18[ -]+mart[ -]*models?\b", "18 mart models"),
    (r"[Mm]arts?\s*\(18\)", "Marts (18)"),
    (r"226\+[ -]*(pytest|tests?)", "226+ pytest/tests"),
    (r"34[ -]+Python[ -]+test[ -]*files?", "34 Python test files"),
    (r"Phase\s+3[ -]*·[ -]*Streamlit", "Phase 3 Streamlit"),
    (r"F:[/\\]RAG[/\\]", "local path F:/RAG/"),
    (r"C:\\Users\\", "local path C:\\Users\\"),
]

ACTIVE_DIRS = [
    PROJECT / "dashboard",
    PROJECT / "docs" / "portfolio",
]
ACTIVE_REPORTS = []

EXCLUDE_PREFIXES = [
    str(PROJECT / "docs" / "archive"),
    str(PROJECT / "reports" / "portfolio" / "archive"),
    str(PROJECT / "reports" / "portfolio" / "releases"),
    str(PROJECT / "reports" / "phase1"),
    str(PROJECT / "reports" / "phase2"),
    str(PROJECT / "reports" / "phase3"),
    str(PROJECT / "reports" / "phase4"),
]


def _collect_text_files(roots, exts=None):
    if exts is None:
        exts = {".py", ".md", ".txt", ".mmd", ".svg"}
    paths = []
    for root in roots:
        rp = PROJECT / root if isinstance(root, str) else root
        if rp.is_file():
            if rp.suffix in exts:
                paths.append(rp)
        elif rp.is_dir():
            for f in rp.rglob("*"):
                if f.suffix in exts and f.is_file():
                    if not any(str(f).startswith(ep) for ep in EXCLUDE_PREFIXES):
                        paths.append(f)
    return list(set(paths))


def _stale_fact_scan():
    text_files = _collect_text_files(ACTIVE_DIRS)
    for f in ACTIVE_REPORTS:
        if f.exists():
            text_files.append(f)
    findings = []
    for fp in sorted(set(text_files)):
        try:
            content = fp.read_text(encoding="utf-8")
        except Exception:
            continue
        lines = content.splitlines()
        for pattern, label in STALE_PATTERNS:
            for m in re.finditer(pattern, content):
                line_no = content[: m.start()].count("\n") + 1
                line_text = lines[line_no - 1] if line_no <= len(lines) else ""
                # Skip lines that correctly mark the numbers as historical
                if re.search(
                    r"\b(?:earlier|historical|previous|old[ -]structure)\b",
                    line_text,
                    re.IGNORECASE,
                ):
                    continue
                ctx = content[max(0, m.start() - 10) : m.end() + 10].replace("\n", " ")
                findings.append(f"{fp.relative_to(PROJECT)}:{line_no}: {label} -> '{ctx.strip()}'")
    return findings


def fail(msg):
    results["failed_gates"].append(msg)
    results["accepted"] = False


def warn(msg):
    results["warnings"].append(msg)


for f in REQUIRED_FILES:
    p = PROJECT / f
    if p.exists() and p.stat().st_size > 0:
        results["passed_gates"].append(f"file:{f}")  # type: ignore[attr-defined]  # pre-existing: object type
    else:
        if "demo" in f or ".sh" in f:
            warn(f"Optional file missing: {f}")
        else:
            fail(f"Missing: {f}")

for s in SCREENSHOTS:
    p = PROJECT / "docs" / "screenshots" / s
    if p.exists():
        with open(p, "rb") as ff:
            if ff.read(4) == b"\x89PNG":
                results["passed_gates"].append(f"screenshot:{s}")  # type: ignore[attr-defined]  # pre-existing: object type
            else:
                fail(f"Invalid PNG: {s}")
    else:
        fail(f"Missing screenshot: {s}")

# Git check
r = subprocess.run(
    ["git", "status", "--porcelain"], capture_output=True, text=True, cwd=str(PROJECT)
)
if r.stdout.strip():
    warn("Working tree has uncommitted changes")

# README content check
readme = (
    (PROJECT / "README.md").read_text(encoding="utf-8") if (PROJECT / "README.md").exists() else ""
)
for keyword in [
    "Synthetic",
    "architecture",
    "dashboard",
    "A/B",
    "root cause",
    "pytest",
    "Limitations",
]:
    if keyword.lower() in readme.lower():
        results["passed_gates"].append(f"readme:{keyword}")  # type: ignore[attr-defined]  # pre-existing: object type
    else:
        fail(f"README missing: {keyword}")

# ── Dynamic project metrics (no hardcoded counts) ──


def count_sql_files(path: Path) -> int:
    return len(list(path.rglob("*.sql")))


# Calculate from code
staging_count = count_sql_files(PROJECT / "dbt_fxfill" / "models" / "staging")
intermediate_count = count_sql_files(PROJECT / "dbt_fxfill" / "models" / "intermediate")
mart_count = count_sql_files(PROJECT / "dbt_fxfill" / "models" / "marts")
dbt_model_count = count_sql_files(PROJECT / "dbt_fxfill" / "models")
singular_test_count = count_sql_files(PROJECT / "dbt_fxfill" / "tests")
dashboard_business_pages = len(
    [f for f in (PROJECT / "dashboard" / "pages").glob("*.py") if f.name != "__init__.py"]
)
dashboard_page_count = 1 + dashboard_business_pages

# Read immutable release evidence for dbt test counts
release_evidence_path = (
    PROJECT
    / "reports"
    / "portfolio"
    / "releases"
    / "portfolio-v1.2.12"
    / "core_release_acceptance.json"
)
generic_test_count = None
release_model_count = None
release_test_total = None
release_gate_count = None
if release_evidence_path.exists():
    with open(release_evidence_path) as f:
        ev = json.load(f)
    dbt_info = ev.get("dbt", {})
    gate_info = ev.get("gate_summary", {})
    generic_test_count = dbt_info.get("generic_test_count")
    release_model_count = dbt_info.get("model_count")
    release_test_total = dbt_info.get("test_definition_count")
    release_gate_count = gate_info.get("required_gate_count")

# Consistency gates
consistency_ok = True
if dbt_model_count != (staging_count + intermediate_count + mart_count):
    fail("dbt model count does not equal staging + intermediate + marts")
    consistency_ok = False
if release_model_count is not None and dbt_model_count != release_model_count:
    fail("Code dbt model count differs from release evidence")
    consistency_ok = False
if singular_test_count > 0 and release_test_total is not None:
    if (
        generic_test_count is not None
        and (generic_test_count + singular_test_count) != release_test_total
    ):
        fail("dbt test count does not equal generic + singular from release evidence")
        consistency_ok = False
if dashboard_page_count != 8:
    fail(f"Dashboard pages expected 8, got {dashboard_page_count}")
    consistency_ok = False

warehouse_objects = 7 + dbt_model_count  # 7 raw + dbt models

results["project_metrics"] = {
    "dbt_models": dbt_model_count,
    "staging_models": staging_count,
    "intermediate_models": intermediate_count,
    "marts": mart_count,
    "warehouse_objects": warehouse_objects,
    "generic_dbt_tests": generic_test_count,
    "singular_dbt_tests": singular_test_count,
    "total_dbt_tests": release_test_total,
    "pages": dashboard_page_count,
    "charts": 30,
    "bootstrap_iterations": 5000,
    "release_tag": "portfolio-v1.2.12",
}

# ── Check explicit count expectations ──
EXPECTED = {
    "staging_count": (staging_count, 7),
    "intermediate_count": (intermediate_count, 13),
    "mart_count": (mart_count, 21),
    "dbt_model_count": (dbt_model_count, 41),
    "warehouse_objects": (warehouse_objects, 48),
    "dashboard_pages": (dashboard_page_count, 8),
    "singular_test_count": (singular_test_count, 23),
    "release_generic_tests": (generic_test_count, 21),
    "release_test_total": (release_test_total, 44),
    "release_model_count": (release_model_count, 41),
    "release_gate_count": (release_gate_count, 11),
}
for name, (actual, expected) in EXPECTED.items():
    if actual is not None and actual != expected:
        fail(f"{name}: expected {expected}, got {actual}")
        consistency_ok = False

# ── Stale-fact scan ──
stale_findings = _stale_fact_scan()
results["stale_fact_findings"] = stale_findings
if stale_findings:
    for sf in stale_findings:
        fail(f"Stale fact: {sf}")
    consistency_ok = False
else:
    results["passed_gates"].append("active_fact_scan")  # type: ignore[attr-defined]

# ── Diagram integrity ──
diagram_ok = True
for stem in ["architecture", "data_flow"]:
    svg = PROJECT / "docs" / "portfolio" / f"{stem}.svg"
    png = PROJECT / "docs" / "portfolio" / f"{stem}.png"
    if not svg.exists() or svg.stat().st_size == 0:
        fail(f"Missing or empty: {svg.relative_to(PROJECT)}")
        diagram_ok = False
    if not png.exists() or png.stat().st_size == 0:
        fail(f"Missing or empty: {png.relative_to(PROJECT)}")
        diagram_ok = False
    if svg.exists():
        svg_text = svg.read_text(encoding="utf-8")
        for pattern, label in STALE_PATTERNS:
            if pattern.startswith("F:") or pattern.startswith("C:"):
                continue
            if re.search(pattern, svg_text):
                fail(f"Diagram {stem}.svg contains stale: {label}")
                diagram_ok = False
if diagram_ok:
    results["passed_gates"].append("diagram_fact_consistency")  # type: ignore[attr-defined]

# ── Screenshot manifest integrity ──
manifest_path = PROJECT / "docs" / "portfolio" / "screenshot_manifest.json"
manifest_ok = True
old_home_hash = "33f8157cc478c888"
if manifest_path.exists():
    import hashlib as _hl

    from PIL import Image as _Img

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if len(manifest) != 8:
        fail(f"Screenshot manifest has {len(manifest)} entries, expected 8")
        manifest_ok = False
    for entry in manifest:
        fn = entry.get("filename", "")
        img_path = PROJECT / "docs" / "screenshots" / fn
        if not img_path.exists():
            fail(f"Screenshot missing: {fn}")
            manifest_ok = False
            continue
        try:
            img = _Img.open(img_path)
            img.verify()
            img = _Img.open(img_path)
            w, h = img.size
            fs = img_path.stat().st_size
            actual_hash = _hl.sha256(img_path.read_bytes()).hexdigest()[:16]
            if w != entry.get("width"):
                fail(f"{fn}: width {w} != manifest {entry.get('width')}")
                manifest_ok = False
            if h != entry.get("height"):
                fail(f"{fn}: height {h} != manifest {entry.get('height')}")
                manifest_ok = False
            if fs != entry.get("file_size_bytes"):
                fail(f"{fn}: size {fs} != manifest {entry.get('file_size_bytes')}")
                manifest_ok = False
            if actual_hash != entry.get("sha256", ""):
                fail(f"{fn}: hash {actual_hash} != manifest {entry.get('sha256')}")
                manifest_ok = False
            if not entry.get("valid_png"):
                fail(f"{fn}: valid_png is false")
                manifest_ok = False
            if fn == "home.png" and entry.get("sha256") == old_home_hash:
                fail(f"home.png still has old hash {old_home_hash}")
                manifest_ok = False
        except Exception as e:
            fail(f"{fn}: invalid PNG: {e}")
            manifest_ok = False
    if manifest_ok:
        results["passed_gates"].append("screenshot_manifest_integrity")  # type: ignore[attr-defined]
else:
    warn("Screenshot manifest not found (screenshot_manifest_integrity skipped)")

# ── Check consistency gate ──
if consistency_ok:
    results["passed_gates"].append("fact_consistency")  # type: ignore[attr-defined]
else:
    fail("Fact consistency gate failed")

with open(R / "portfolio_acceptance.json", "w") as f:  # type: ignore[assignment]  # pre-existing: TextIOWrapper vs str
    json.dump(results, f, indent=2, default=str)  # type: ignore[arg-type]  # pre-existing: str vs SupportsWrite
md = [
    "# Portfolio Acceptance\n",
    f"Accepted: **{results['accepted']}**\n",
    f"Passed: {len(results['passed_gates'])}, Failed: {len(results['failed_gates'])}\n",  # type: ignore[arg-type]  # pre-existing: object vs Sized
]
with open(R / "portfolio_acceptance.md", "w") as f:  # type: ignore[assignment]  # pre-existing: TextIOWrapper vs str
    f.write("".join(md))  # type: ignore[attr-defined]  # pre-existing: str type

if results["accepted"]:
    print("PORTFOLIO ACCEPTANCE PASSED")
    sys.exit(0)
else:
    print(f"PORTFOLIO ACCEPTANCE FAILED: {len(results['failed_gates'])} gates")  # type: ignore[arg-type]  # pre-existing: object vs Sized
    for g in results["failed_gates"][:5]:  # type: ignore[index]  # pre-existing: object not indexable
        print(f"  - {g}")
    sys.exit(1)
