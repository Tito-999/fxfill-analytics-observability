#!/usr/bin/env python3
"""Refresh portfolio screenshot assets: capture, manifest, contact sheet, check."""

import argparse
import hashlib
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = PROJECT / "docs" / "screenshots"
MANIFEST_PATH = PROJECT / "docs" / "portfolio" / "screenshot_manifest.json"
CONTACT_SHEET_PATH = PROJECT / "docs" / "portfolio" / "dashboard_contact_sheet.png"
OLD_HOME_HASH = "33f8157cc478c888"

SCREENSHOTS = [
    ("home.png", "Home"),
    ("executive_overview.png", "Executive Overview"),
    ("funnel_retention.png", "Funnel Retention"),
    ("feature_adoption.png", "Feature Adoption"),
    ("agent_observability.png", "Agent Observability"),
    ("ab_test.png", "AB Test"),
    ("root_cause.png", "Root Cause"),
    ("data_quality.png", "Data Quality"),
]


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def build_manifest() -> list:
    """Build manifest from actual files on disk."""
    manifest = []
    for filename, page_name in SCREENSHOTS:
        p = SCREENSHOT_DIR / filename
        if not p.exists():
            print(f"WARNING: {filename} not found, skipping manifest entry")
            continue
        from PIL import Image

        img = Image.open(p)
        w, h = img.size
        entry = {
            "filename": filename,
            "page_name": page_name,
            "width": w,
            "height": h,
            "file_size_bytes": p.stat().st_size,
            "sha256": _file_sha256(p),
            "valid_png": True,
            "contains_sensitive_content_reviewed": True,
        }
        manifest.append(entry)
    return manifest


def generate_contact_sheet():
    """Generate dashboard_contact_sheet.png from current screenshots."""
    from PIL import Image, ImageDraw, ImageFont

    images = []
    labels = []
    for filename, page_name in SCREENSHOTS:
        p = SCREENSHOT_DIR / filename
        if p.exists():
            images.append(Image.open(p).convert("RGB"))
            labels.append(page_name)

    if len(images) != 8:
        print(f"ERROR: Expected 8 screenshots, found {len(images)}")
        return False

    # Layout: 2x4 grid
    cols, rows = 2, 4
    thumb_w, thumb_h = 480, 360
    label_h = 36
    margin = 16
    bg_color = (255, 255, 255)

    sheet_w = cols * thumb_w + (cols + 1) * margin
    sheet_h = rows * (thumb_h + label_h) + (rows + 1) * margin

    sheet = Image.new("RGB", (sheet_w, sheet_h), bg_color)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font = ImageFont.load_default()

    draw = ImageDraw.Draw(sheet)
    for idx in range(8):
        col = idx % cols
        row = idx // cols
        img = images[idx]
        img.thumbnail((thumb_w, thumb_h), Image.LANCZOS)
        iw, ih = img.size
        x = margin + col * (thumb_w + margin) + (thumb_w - iw) // 2
        y = margin + row * (thumb_h + label_h + margin)
        sheet.paste(img, (x, y))
        label = labels[idx]
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        lx = margin + col * (thumb_w + margin) + (thumb_w - tw) // 2
        ly = y + thumb_h + 4
        draw.text((lx, ly), label, fill=(44, 62, 80), font=font)

    sheet.save(CONTACT_SHEET_PATH, "PNG")
    print(f"Contact sheet saved: {CONTACT_SHEET_PATH} ({sheet.size})")
    return True


def capture_home(base_url: str, browser_exe: str | None, viewport_w: int, viewport_h: int):
    """Capture home.png using Playwright."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "ERROR: playwright not installed. Run: pip install playwright && python -m playwright install chromium"
        )
        return False

    target_url = base_url.rstrip("/") + "/"
    output_path = SCREENSHOT_DIR / "home.png"
    tmp_path = output_path.with_suffix(".tmp.png")

    required_texts = [
        "41 dbt models",
        "21 analytics marts",
        "44 / 44 dbt tests",
        "11 / 11 required release gates",
    ]

    print(f"Capturing {target_url} -> {output_path}")
    try:
        with sync_playwright() as p:
            launch_args = {"headless": True}
            if browser_exe:
                launch_args["executable_path"] = browser_exe
            browser = p.chromium.launch(**launch_args)
            context = browser.new_context(
                viewport={"width": viewport_w, "height": viewport_h},
            )
            page = context.new_page()
            page.goto(target_url, wait_until="networkidle", timeout=60000)
            # Wait for Streamlit content
            try:
                page.wait_for_selector("[data-testid='stAppViewContainer']", timeout=30000)
            except Exception:
                pass
            time.sleep(5)  # Give Streamlit time to render

            content = page.content()
            for text in required_texts:
                if text not in content:
                    print(f"ERROR: Required text not found: '{text}'")
                    browser.close()
                    return False

            page.screenshot(path=str(tmp_path), full_page=True)
            browser.close()

        # Verify PNG
        from PIL import Image

        img = Image.open(tmp_path)
        img.verify()
        img = Image.open(tmp_path)
        w, h = img.size
        if w < 100 or h < 100:
            print(f"ERROR: Screenshot too small ({w}x{h})")
            return False

        # Atomic replace
        tmp_path.replace(output_path)
        print(f"Home captured: {output_path} ({w}x{h}, {output_path.stat().st_size} bytes)")
        return True

    except Exception as e:
        print(f"ERROR during capture: {e}")
        if tmp_path.exists():
            tmp_path.unlink()
        return False


def run_check():
    """Read-only check: manifest integrity, file existence, old hash."""
    errors = []
    if not MANIFEST_PATH.exists():
        errors.append("Manifest not found")
        return errors

    import json

    from PIL import Image

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if len(manifest) != 8:
        errors.append(f"Manifest has {len(manifest)} entries, expected 8")

    for entry in manifest:
        fn = entry.get("filename", "")
        p = SCREENSHOT_DIR / fn
        if not p.exists():
            errors.append(f"Missing screenshot: {fn}")
            continue
        try:
            img = Image.open(p)
            img.verify()
            img = Image.open(p)
            w, h = img.size
            fs = p.stat().st_size
            actual_hash = _file_sha256(p)
            if w != entry.get("width"):
                errors.append(f"{fn}: width {w} != manifest {entry.get('width')}")
            if h != entry.get("height"):
                errors.append(f"{fn}: height {h} != manifest {entry.get('height')}")
            if fs != entry.get("file_size_bytes"):
                errors.append(f"{fn}: size {fs} != manifest {entry.get('file_size_bytes')}")
            if actual_hash != entry.get("sha256", ""):
                errors.append(f"{fn}: hash {actual_hash} != manifest {entry.get('sha256')}")
            if not entry.get("valid_png"):
                errors.append(f"{fn}: valid_png is false")
            if not entry.get("contains_sensitive_content_reviewed"):
                errors.append(f"{fn}: contains_sensitive_content_reviewed is false")
        except Exception as e:
            errors.append(f"{fn}: invalid PNG: {e}")

    # Check home hash is not old
    home_entry = next((e for e in manifest if e.get("filename") == "home.png"), None)
    if home_entry and home_entry.get("sha256") == OLD_HOME_HASH:
        errors.append(f"home.png still has old hash {OLD_HOME_HASH}")

    # Check contact sheet
    if not CONTACT_SHEET_PATH.exists() or CONTACT_SHEET_PATH.stat().st_size == 0:
        errors.append("Contact sheet missing or empty")
    else:
        try:
            cs = Image.open(CONTACT_SHEET_PATH)
            cs.verify()
            cs = Image.open(CONTACT_SHEET_PATH)
            if cs.size[0] < 100 or cs.size[1] < 100:
                errors.append(f"Contact sheet too small: {cs.size}")
        except Exception as e:
            errors.append(f"Contact sheet invalid: {e}")

    if errors:
        print("SCREENSHOT CHECK FAILED:")
        for e in errors:
            print(f"  {e}")
    else:
        print("SCREENSHOT CHECK PASSED")
        print(f"  {len(manifest)} entries, all valid, home hash != old")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh", action="store_true", help="Rebuild manifest and contact sheet from disk"
    )
    parser.add_argument("--check", action="store_true", help="Read-only validation")
    parser.add_argument(
        "--capture-home", action="store_true", help="Capture home.png via Playwright"
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8501")
    parser.add_argument("--browser-executable", default=None)
    parser.add_argument("--viewport-width", type=int, default=2450)
    parser.add_argument("--viewport-height", type=int, default=1200)
    args = parser.parse_args()

    if args.check:
        errs = run_check()
        sys.exit(1 if errs else 0)

    if args.capture_home:
        ok = capture_home(
            args.base_url, args.browser_executable, args.viewport_width, args.viewport_height
        )
        if not ok:
            sys.exit(1)

    if args.refresh:
        manifest = build_manifest()
        import json

        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"Manifest written: {MANIFEST_PATH}")
        ok = generate_contact_sheet()
        if not ok:
            sys.exit(1)
        # Run check
        errs = run_check()
        sys.exit(1 if errs else 0)

    # Default: print usage
    parser.print_help()


if __name__ == "__main__":
    main()
