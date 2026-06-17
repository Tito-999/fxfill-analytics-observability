"""Verify 8 dashboard screenshots exist as valid PNGs with proper dimensions."""

from pathlib import Path

from PIL import Image

PROJECT = Path(__file__).resolve().parent.parent.parent
SCREENSHOTS_DIR = PROJECT / "docs" / "screenshots"

EXPECTED = [
    "home.png",
    "executive_overview.png",
    "funnel_retention.png",
    "feature_adoption.png",
    "agent_observability.png",
    "ab_test.png",
    "root_cause.png",
    "data_quality.png",
]


def test_screenshots_dir_exists():
    assert SCREENSHOTS_DIR.exists()


def test_eight_screenshots_present():
    for fname in EXPECTED:
        path = SCREENSHOTS_DIR / fname
        assert path.exists(), f"Missing: {fname}"
        assert path.stat().st_size > 1000, f"Too small: {fname}"


def test_all_are_valid_pngs():
    for fname in EXPECTED:
        path = SCREENSHOTS_DIR / fname
        with open(path, "rb") as f:
            assert f.read(8)[:4] == b"\x89PNG", f"Not PNG: {fname}"


def test_all_have_minimum_width():
    for fname in EXPECTED:
        img = Image.open(SCREENSHOTS_DIR / fname)
        assert img.width >= 1200, f"{fname} width {img.width} < 1200"
        assert img.height >= 600, f"{fname} height {img.height} < 600"
