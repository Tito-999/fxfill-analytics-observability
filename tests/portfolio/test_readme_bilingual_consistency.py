"""Verify bilingual README consistency — EN/zh-CN sync, encoding, structure."""

import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent.parent

EN_PATH = PROJECT / "README.md"
ZH_PATH = PROJECT / "README.zh-CN.md"
CHECKER_PATH = PROJECT / "scripts" / "check_readme_bilingual_consistency.py"

# Re-use checker functions directly to avoid duplicating parsing logic
sys.path.insert(0, str(PROJECT / "scripts"))
from check_readme_bilingual_consistency import (  # noqa: E402  # type: ignore[import-not-found]
    LANGUAGE_LINKS,
    _check_both_conflict_markers,
    _check_code_blocks,
    _check_conflict_markers,
    _check_images,
    _check_links,
    _check_numeric_facts,
    _check_sync_markers,
    _check_tables,
    _extract_code_blocks,
    _extract_image_paths,
    _extract_numeric_tokens,
    _extract_sync_markers,
    _read_utf8,
    _strip_non_visible_syntax,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Conflict marker detection
# ═══════════════════════════════════════════════════════════════════════════════


def test_conflict_markers_are_rejected():
    """Any Git conflict marker in either README must fail the check."""
    # All three marker patterns with realistic surrounding text
    for marker_text in [
        "<<<<<<< HEAD",
        "=======",
        ">>>>>>> branch-name",
    ]:
        errors = _check_conflict_markers(marker_text, "TEST")
        assert len(errors) >= 1, f"Should detect conflict marker: {marker_text!r}"

    # Clean text should pass
    errors = _check_conflict_markers("# Normal heading\nSome content\nMore content", "TEST")
    assert errors == [], f"Clean text should have no errors, got: {errors}"

    # The combined checker should work on both
    en = "## Overview\nNo conflicts here."
    zh = "## 概览\nNo conflicts here."
    assert _check_both_conflict_markers(en, zh) == []

    # Conflict in ZH only
    en2 = "## Overview\nclean"
    zh2 = "<<<<<<< HEAD\nconflict\n=======\nother\n>>>>>>>"
    errors2 = _check_both_conflict_markers(en2, zh2)
    assert len(errors2) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# Numeric extraction — badge URLs excluded
# ═══════════════════════════════════════════════════════════════════════════════


def test_numeric_extraction_ignores_badge_urls():
    """Numbers embedded in badge image URLs must NOT appear in numeric facts."""
    text = (
        "[![406 Tests]"
        "(https://img.shields.io/badge/Tests-406%20%2F%20406%20passed-brightgreen.svg)]"
        "(https://github.com/Tito-999/fxfill-analytics-observability)\n"
        "The project has 406 tests.\n"
    )
    tokens = _extract_numeric_tokens(text)
    token_set = set(tokens.keys())

    # Visible prose number is kept
    assert "406" in token_set, "Visible '406' must be extracted from prose"

    # URL-encoded fragments from badge URL are excluded
    for spurious in ["20", "20406", "999"]:
        assert spurious not in token_set, (
            f"Spurious '{spurious}' from badge URL must NOT appear in numeric facts; "
            f"got: {sorted(token_set)}"
        )


def test_numeric_extraction_ignores_badge_urls_multiple():
    """All badge rows (Tests, Models, Tests) are stripped before extraction."""
    text = (
        "[![406 Tests](https://img.shields.io/badge/Tests-406%20%2F%20406%20passed-brightgreen.svg)](...)\n"
        "[![dbt Models](https://img.shields.io/badge/dbt%20Models-41%20%2F%2041-brightgreen.svg)](...)\n"
        "[![dbt Tests](https://img.shields.io/badge/dbt%20Tests-44%20%2F%2044-brightgreen.svg)](...)\n"
    )
    tokens = _extract_numeric_tokens(text)
    token_set = set(tokens.keys())

    for spurious in ["20", "20406", "2041", "2044"]:
        assert (
            spurious not in token_set
        ), f"Spurious '{spurious}' from badge URLs must NOT appear; got: {sorted(token_set)}"


def test_numeric_extraction_ignores_image_urls():
    """Numbers in image paths/URLs must NOT appear in numeric facts."""
    text = "![chart-42](docs/portfolio/chart_2024_v2.png)\n" "The chart shows 42 data points.\n"
    tokens = _extract_numeric_tokens(text)
    token_set = set(tokens.keys())

    # Only the visible prose number
    assert "42" in token_set, "Visible '42' in prose must be extracted"
    # Image URL fragments are stripped
    for spurious in ["2024", "2"]:
        assert (
            spurious not in token_set
        ), f"Spurious '{spurious}' from image URL must NOT appear; got: {sorted(token_set)}"


# ═══════════════════════════════════════════════════════════════════════════════
# Numeric extraction — Markdown link targets excluded
# ═══════════════════════════════════════════════════════════════════════════════


def test_numeric_extraction_ignores_markdown_link_targets():
    """Numbers appearing ONLY in link-target URLs must not be extracted."""
    text = (
        "See the [release v1.2.12]"
        "(https://github.com/Tito-999/fxfill-analytics-observability/releases/tag/v1.2.12).\n"
    )
    tokens = _extract_numeric_tokens(text)
    token_set = set(tokens.keys())

    # Visible link text 'v1.2.12' IS kept
    assert "v1.2.12" in token_set, "Visible 'v1.2.12' in link text must be extracted"

    # '999' from 'Tito-999' in the URL target must NOT appear
    assert (
        "999" not in token_set
    ), f"'999' from URL path must NOT appear in numeric facts; got: {sorted(token_set)}"


def test_numeric_extraction_link_text_kept_target_stripped():
    """Visible link text numbers stay; URL target numbers do not."""
    text = "Version [3.11](https://example.com/download/3.11.0/package-3.11.tar.gz) is required.\n"
    tokens = _extract_numeric_tokens(text)
    token_set = set(tokens.keys())

    # '3.11' from visible link text is kept
    assert "3.11" in token_set

    # '0' from '3.11.0' in URL is stripped (the whole URL target is removed)
    # '3.11.0' as a token wouldn't match _NUMERIC_TOKEN_RE anyway (no \d+.\d+.\d+ pattern
    # without the v prefix), but '3.11' from the URL could. With stripping,
    # only one '3.11' (from the visible text) remains.
    assert tokens.get("3.11", 0) == 1, f"Expected one '3.11' from visible text, got: {dict(tokens)}"


# ═══════════════════════════════════════════════════════════════════════════════
# Visible numeric facts are still compared
# ═══════════════════════════════════════════════════════════════════════════════


def test_visible_numeric_facts_are_still_compared():
    """_check_numeric_facts must still detect mismatches in visible prose numbers."""
    en = "The pipeline has 406 tests and 41 models.\n"
    zh = "The pipeline has 428 tests and 41 models.\n"  # 406 vs 428 — mismatch

    errors = _check_numeric_facts(en, zh)
    assert len(errors) >= 1, f"Should detect 406-vs-428 mismatch, got: {errors}"
    assert any(
        "406" in e or "428" in e for e in errors
    ), f"Error should mention the mismatched numbers: {errors}"


def test_visible_numeric_facts_match_when_identical():
    """Identical visible numbers must pass the check."""
    en = "The pipeline has 406 tests and 41 models. Release v1.2.12.\n"
    zh = "管道有 406 个测试和 41 个模型。发布版本 v1.2.12。\n"

    errors = _check_numeric_facts(en, zh)
    assert errors == [], f"Identical numbers should pass, got: {errors}"


def test_numeric_facts_ignore_badge_urls_in_comparison():
    """_check_numeric_facts with badge-heavy text must only compare visible numbers."""
    en = (
        "[![406 Tests](https://img.shields.io/badge/Tests-406%20%2F%20406-brightgreen.svg)](x)\n"
        "pytest: 406 / 406 passed\n"
    )
    zh = (
        "[![406 Tests](https://img.shields.io/badge/Tests-406%20%2F%20406-brightgreen.svg)](x)\n"
        "pytest：406 / 406 通过\n"
    )
    errors = _check_numeric_facts(en, zh)
    assert errors == [], f"Badge URL numbers must be ignored; got: {errors}"


# ═══════════════════════════════════════════════════════════════════════════════
# Language navigation difference is allowed
# ═══════════════════════════════════════════════════════════════════════════════


def test_language_navigation_difference_is_allowed():
    """Language-switch links may differ; all other links must match."""
    en = (
        "**English** | [简体中文](./README.zh-CN.md)\n\n"
        "# Title\n\n"
        "See [the docs](https://example.com/docs) and [GitHub](https://github.com/user/repo).\n"
        "![logo](docs/logo.png)\n\n"
        "Final sentence.\n"
    )
    zh = (
        "[English](./README.md) | **简体中文**\n\n"
        "# 标题\n\n"
        "参见[文档](https://example.com/docs) 和 [GitHub](https://github.com/user/repo)。\n"
        "![logo](docs/logo.png)\n\n"
        "最后一句。\n"
    )

    links_errs = _check_links(en, zh)
    assert (
        links_errs == []
    ), f"Language nav links should be excluded from link check; got: {links_errs}"

    # Numeric facts should also pass (no spurious numbers from language nav file names)
    nums_errs = _check_numeric_facts(en, zh)
    assert (
        nums_errs == []
    ), f"Language nav file names should not affect numeric facts; got: {nums_errs}"

    # Verify both language-switch links are present
    assert "./README.zh-CN.md" in en, "EN must link to zh-CN"
    assert "./README.md" in zh, "ZH must link to EN"


def test_language_navigation_links_are_in_language_links_set():
    """The language-switch filenames must be in LANGUAGE_LINKS."""
    assert "./README.md" in LANGUAGE_LINKS
    assert "./README.zh-CN.md" in LANGUAGE_LINKS
    assert "README.md" in LANGUAGE_LINKS
    assert "README.zh-CN.md" in LANGUAGE_LINKS


def test_language_navigation_mismatch_outside_nav_is_still_caught():
    """A link difference outside the language nav must still be flagged."""
    en = (
        "**English** | [简体中文](./README.zh-CN.md)\n\n"
        "# Title\n\n"
        "See [our docs](https://example.com/docs-v1).\n"
    )
    zh = (
        "[English](./README.md) | **简体中文**\n\n"
        "# 标题\n\n"
        "参见[我们的文档](https://example.com/docs-v2)。\n"  # different URL!
    )
    links_errs = _check_links(en, zh)
    assert (
        len(links_errs) >= 1
    ), f"Should flag link target difference outside language nav; got: {links_errs}"


# ═══════════════════════════════════════════════════════════════════════════════
# strip_non_visible_syntax unit tests
# ═══════════════════════════════════════════════════════════════════════════════


def test_strip_removes_code_blocks():
    text = "Before\n```python\nprint(42)\n```\nAfter with 42.\n"
    cleaned = _strip_non_visible_syntax(text)
    assert "print(42)" not in cleaned, "Code block content must be stripped"
    assert "42" in cleaned, "Visible '42' after code block must remain"


def test_strip_removes_image_markdown():
    text = "![chart-2024](docs/img_2024_v3.png) shows 2024 data.\n"
    cleaned = _strip_non_visible_syntax(text)
    assert "img_2024" not in cleaned, "Image path must be stripped"
    assert "v3" not in cleaned, "Image filename version must be stripped"
    assert "2024" in cleaned, "Visible '2024' in prose must remain"


def test_strip_replaces_links_with_text():
    text = "Click [here for v2.0](https://cdn.example.com/releases/v2.0/download).\n"
    cleaned = _strip_non_visible_syntax(text)
    assert "cdn.example.com" not in cleaned, "URL domain must be stripped"
    assert "v2.0" in cleaned, "Visible 'v2.0' in link text must remain"


# ── File existence and encoding ────────────────────────────────────────────


def test_bilingual_readme_files_exist():
    """Both README files must exist."""
    assert EN_PATH.exists(), f"Missing: {EN_PATH}"
    assert ZH_PATH.exists(), f"Missing: {ZH_PATH}"


def test_bilingual_readme_no_mojibake():
    """Neither README may contain mojibake or encoding errors."""
    for path in [EN_PATH, ZH_PATH]:
        text, errors = _read_utf8(path)
        assert text is not None, f"{path.name}: failed to read as UTF-8"
        assert errors == [], f"{path.name}: encoding/mojibake issues: {errors}"


# ── Sync markers ────────────────────────────────────────────────────────────


def test_bilingual_readme_sync_markers_match():
    """Sync markers must be identical in count, ID, and order."""
    en_text = EN_PATH.read_text(encoding="utf-8")
    zh_text = ZH_PATH.read_text(encoding="utf-8")
    errors = _check_sync_markers(en_text, zh_text)
    assert errors == [], f"Sync marker issues: {errors}"


def test_bilingual_readme_sync_markers_present():
    """Both READMEs must contain sync markers."""
    en_text = EN_PATH.read_text(encoding="utf-8")
    zh_text = ZH_PATH.read_text(encoding="utf-8")
    en_markers = _extract_sync_markers(en_text)
    zh_markers = _extract_sync_markers(zh_text)
    assert len(en_markers) > 0, "EN README has no sync markers"
    assert len(zh_markers) > 0, "ZH README has no sync markers"
    assert (
        en_markers == zh_markers
    ), f"Sync marker mismatch:\n  EN: {en_markers}\n  ZH: {zh_markers}"


# ── Images ──────────────────────────────────────────────────────────────────


def test_bilingual_readme_images_exist():
    """All referenced local images must exist on disk."""
    en_text = EN_PATH.read_text(encoding="utf-8")
    zh_text = ZH_PATH.read_text(encoding="utf-8")
    for label, text in [("EN", en_text), ("ZH", zh_text)]:
        for img_path in _extract_image_paths(text):
            if img_path.startswith(("http://", "https://")):
                continue
            full = PROJECT / img_path
            assert full.exists(), f"{label}: image not found: {img_path}"


def test_bilingual_readme_images_match():
    """Image paths must be identical between EN and ZH."""
    en_text = EN_PATH.read_text(encoding="utf-8")
    zh_text = ZH_PATH.read_text(encoding="utf-8")
    errors = _check_images(en_text, zh_text)
    assert errors == [], f"Image mismatch: {errors}"


# ── Code blocks ─────────────────────────────────────────────────────────────


def test_bilingual_readme_code_blocks_match():
    """Fenced code blocks must be byte-identical between EN and ZH."""
    en_text = EN_PATH.read_text(encoding="utf-8")
    zh_text = ZH_PATH.read_text(encoding="utf-8")
    errors = _check_code_blocks(en_text, zh_text)
    assert errors == [], f"Code block mismatch: {errors}"


def test_bilingual_readme_code_block_count():
    """Both READMEs must have the same number of code blocks."""
    en_text = EN_PATH.read_text(encoding="utf-8")
    zh_text = ZH_PATH.read_text(encoding="utf-8")
    en_blocks = _extract_code_blocks(en_text)
    zh_blocks = _extract_code_blocks(zh_text)
    assert len(en_blocks) == len(
        zh_blocks
    ), f"Code block count: EN={len(en_blocks)}, ZH={len(zh_blocks)}"


# ── Numeric facts ───────────────────────────────────────────────────────────


def test_bilingual_readme_numeric_facts_match():
    """Numeric token multiset must be identical between EN and ZH."""
    en_text = EN_PATH.read_text(encoding="utf-8")
    zh_text = ZH_PATH.read_text(encoding="utf-8")
    errors = _check_numeric_facts(en_text, zh_text)
    assert errors == [], f"Numeric fact issues: {errors}"


def test_bilingual_readme_key_numbers_present():
    """Key project numbers must appear in both READMEs."""
    en_text = EN_PATH.read_text(encoding="utf-8")
    zh_text = ZH_PATH.read_text(encoding="utf-8")
    key_numbers = ["406", "41", "44", "11", "7", "13", "21", "8", "20"]
    en_tokens = set(_extract_numeric_tokens(en_text).keys())
    zh_tokens = set(_extract_numeric_tokens(zh_text).keys())
    for num in key_numbers:
        assert num in en_tokens, f"EN missing key number: {num}"
        assert num in zh_tokens, f"ZH missing key number: {num}"


# ── Links ───────────────────────────────────────────────────────────────────


def test_bilingual_readme_links_match():
    """Link targets (except language switch) must be identical."""
    en_text = EN_PATH.read_text(encoding="utf-8")
    zh_text = ZH_PATH.read_text(encoding="utf-8")
    errors = _check_links(en_text, zh_text)
    assert errors == [], f"Link mismatch: {errors}"


def test_bilingual_readme_language_switch_links():
    """Language-switch links must point to the other README."""
    en_text = EN_PATH.read_text(encoding="utf-8")
    zh_text = ZH_PATH.read_text(encoding="utf-8")
    assert "./README.zh-CN.md" in en_text, "EN README must link to zh-CN"
    assert "./README.md" in zh_text, "ZH README must link to EN"


# ── Conflict markers ────────────────────────────────────────────────────────


def test_bilingual_readme_no_conflict_markers():
    """Neither README may contain Git conflict markers."""
    for label, path in [("EN", EN_PATH), ("ZH", ZH_PATH)]:
        text = path.read_text(encoding="utf-8")
        errors = _check_conflict_markers(text, label)
        assert errors == [], f"{label}: conflict markers found: {errors}"


# ── Tables ──────────────────────────────────────────────────────────────────


def test_bilingual_readme_tables_match():
    """Table structure and numeric cells must be consistent."""
    en_text = EN_PATH.read_text(encoding="utf-8")
    zh_text = ZH_PATH.read_text(encoding="utf-8")
    errors = _check_tables(en_text, zh_text)
    assert errors == [], f"Table mismatch: {errors}"


# ── No absolute paths ───────────────────────────────────────────────────────


def test_bilingual_readme_no_absolute_paths():
    """READMEs must not contain machine-specific absolute paths."""
    for label, path in [("EN", EN_PATH), ("ZH", ZH_PATH)]:
        text = path.read_text(encoding="utf-8")
        for pattern in ["F:\\\\", "C:\\\\Users\\\\", "/home/"]:
            assert pattern not in text, f"{label}: absolute path pattern found: {pattern}"


# ── Integration: run the checker script ─────────────────────────────────────


def test_bilingual_readme_consistency_script_passes():
    """The checker script must exit 0 and print the PASSED banner."""
    result = subprocess.run(
        [sys.executable, str(CHECKER_PATH)],
        cwd=str(PROJECT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert (
        result.returncode == 0
    ), f"Checker exited {result.returncode}.\nSTDERR:\n{result.stderr}\nSTDOUT:\n{result.stdout}"
    assert (
        "BILINGUAL_README_CONSISTENCY_PASSED" in result.stdout
    ), "Checker must output the PASSED banner"
