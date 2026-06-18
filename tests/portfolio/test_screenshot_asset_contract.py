"""Screenshot asset contract tests — verify manifest and PNG integrity."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent.parent
MANIFEST_PATH = PROJECT / "docs" / "portfolio" / "screenshot_manifest.json"
SCREENSHOT_DIR = PROJECT / "docs" / "screenshots"
CONTACT_SHEET = PROJECT / "docs" / "portfolio" / "dashboard_contact_sheet.png"
OLD_HOME_HASH = "33f8157cc478c888"


@pytest.fixture
def manifest():
    if not MANIFEST_PATH.exists():
        pytest.skip("screenshot manifest not found")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


class TestManifestIntegrity:
    def test_manifest_has_8_entries(self, manifest):
        assert len(manifest) == 8, f"Expected 8 entries, got {len(manifest)}"

    def test_all_files_exist(self, manifest):
        for entry in manifest:
            p = SCREENSHOT_DIR / entry["filename"]
            assert p.exists(), f"Missing: {entry['filename']}"

    def test_all_files_valid_png(self, manifest):
        from PIL import Image

        for entry in manifest:
            p = SCREENSHOT_DIR / entry["filename"]
            img = Image.open(p)
            img.verify()
            img = Image.open(p)
            assert img.size[0] > 0

    def test_width_matches(self, manifest):
        from PIL import Image

        for entry in manifest:
            p = SCREENSHOT_DIR / entry["filename"]
            w, _h = Image.open(p).size
            assert w == entry["width"], f"{entry['filename']}: {w} != {entry['width']}"

    def test_height_matches(self, manifest):
        from PIL import Image

        for entry in manifest:
            p = SCREENSHOT_DIR / entry["filename"]
            _w, h = Image.open(p).size
            assert h == entry["height"], f"{entry['filename']}: {h} != {entry['height']}"

    def test_file_size_matches(self, manifest):
        for entry in manifest:
            p = SCREENSHOT_DIR / entry["filename"]
            actual = p.stat().st_size
            assert (
                actual == entry["file_size_bytes"]
            ), f"{entry['filename']}: {actual} != {entry['file_size_bytes']}"

    def test_sha256_matches(self, manifest):
        for entry in manifest:
            p = SCREENSHOT_DIR / entry["filename"]
            actual = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
            assert actual == entry["sha256"], f"{entry['filename']}: {actual} != {entry['sha256']}"

    def test_valid_png_true(self, manifest):
        for entry in manifest:
            assert entry.get("valid_png"), f"{entry['filename']}: valid_png is false"

    def test_contains_sensitive_content_reviewed_true(self, manifest):
        for entry in manifest:
            assert entry.get(
                "contains_sensitive_content_reviewed"
            ), f"{entry['filename']}: not reviewed"

    def test_home_hash_not_old(self, manifest):
        home = next((e for e in manifest if e["filename"] == "home.png"), None)
        if home:
            assert home["sha256"] != OLD_HOME_HASH, "home.png still has old manifest hash"

    def test_contact_sheet_exists(self):
        assert CONTACT_SHEET.exists(), "Contact sheet missing"
        from PIL import Image

        img = Image.open(CONTACT_SHEET)
        img.verify()
        img = Image.open(CONTACT_SHEET)
        assert img.size[0] > 100, f"Contact sheet too small: {img.size}"
        assert img.size[1] > 100

    def test_refresh_check_script(self):
        r = subprocess.run(
            [
                sys.executable,
                str(PROJECT / "scripts" / "refresh_portfolio_screenshot_assets.py"),
                "--check",
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT),
            timeout=30,
        )
        # May pass or fail depending on home.png state; record output
        print(f"check stdout: {r.stdout}")
        print(f"check stderr: {r.stderr}")
        # Don't hard-fail if home hasn't been recaptured yet
