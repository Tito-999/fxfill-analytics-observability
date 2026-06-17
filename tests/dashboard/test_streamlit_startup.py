"""Verify dashboard pages are valid Python and Streamlit can be invoked."""
import subprocess, sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent.parent


def test_all_page_files_exist():
    """Verify 1 Home + 7 business pages = 8 total."""
    home = PROJECT / "dashboard" / "Home.py"
    pages = sorted([p for p in (PROJECT / "dashboard" / "pages").glob("*.py")
                    if p.name != "__init__.py"])
    assert home.exists()
    assert len(pages) == 7, f"Expected 7 business pages, found {len(pages)}: {[p.name for p in pages]}"


def test_all_pages_have_valid_syntax():
    """Verify all 8 page files parse as valid Python."""
    pages = sorted([p for p in (PROJECT / "dashboard" / "pages").glob("*.py")
                    if p.name != "__init__.py"])
    page_files = [PROJECT / "dashboard" / "Home.py"] + pages
    assert len(page_files) == 8, f"Expected 8, got {len(page_files)}"
    for pf in page_files:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(pf)],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0, f"Syntax error in {pf.name}: {result.stderr[:200]}"


def test_streamlit_can_be_invoked():
    """Verify `streamlit run dashboard/Home.py --help` does not crash."""
    result = subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(PROJECT / "dashboard" / "Home.py"), "--help"],
        capture_output=True, text=True, timeout=15,
        cwd=str(PROJECT),
    )
    # Streamlit --help returns non-zero, but should not crash with ImportError
    assert "ImportError" not in result.stderr
    assert "ModuleNotFoundError" not in result.stderr
