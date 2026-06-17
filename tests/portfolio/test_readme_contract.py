"""Verify README accuracy for public release."""
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent.parent


def test_readme_author_is_name():
    text = (PROJECT / "README.md").read_text(encoding="utf-8")
    assert "Chengren Pang" in text, "README should name the actual author"
    assert "[Your Name]" not in text, "README should not contain placeholder"


def test_readme_no_wrong_dirs():
    text = (PROJECT / "README.md").read_text(encoding="utf-8")
    assert "dbt_fxfill/" in text, "README should reference dbt_fxfill/"
    assert "dashboard/" in text, "README should reference dashboard/"
    assert "streamlit_app/" not in text, "README should not reference nonexistent streamlit_app/"
    assert "dbt/\n" not in text or "├── dbt/" not in text, "README should not reference dbt/ alone"


def test_readme_no_phase0_or_planned():
    text = (PROJECT / "README.md").read_text(encoding="utf-8")
    assert "Phase 0" not in text, "README should not mention Phase 0"
    assert "Key Features (Planned)" not in text, "README should not list planned features"


def test_readme_no_fake_ci():
    text = (PROJECT / "README.md").read_text(encoding="utf-8")
    assert "clean CI status" not in text, "README should not claim CI"


def test_readme_tags_updated():
    text = (PROJECT / "README.md").read_text(encoding="utf-8")
    assert "portfolio-v1.2" in text, "README should list portfolio-v1.2 tag"


def test_readme_no_fastapi_core():
    text = (PROJECT / "README.md").read_text(encoding="utf-8")
    assert "FastAPI event collector" not in text


def test_setup_script_checks():
    text = (PROJECT / "scripts/setup_portfolio.ps1").read_text(encoding="utf-8")
    assert "conda run" not in text, "Setup script should not use conda run"
    assert "PYTHONNOUSERSITE" in text
    assert '$LASTEXITCODE -ne 0' in text, "Setup script should check exit codes"


def test_run_script_checks():
    text = (PROJECT / "scripts/run_portfolio_demo.ps1").read_text(encoding="utf-8")
    assert "warehouse/fxfill.duckdb" in text, "Run script should check DB exists"
    assert "TcpClient" in text or "Get-NetTCPConnection" in text, "Run script should check port"
