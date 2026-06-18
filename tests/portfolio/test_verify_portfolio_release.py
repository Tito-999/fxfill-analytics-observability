"""Tests for stale-fact scanner patterns used by verify_portfolio_release.py."""

import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent.parent

# Mirror of STALE_PATTERNS from verify_portfolio_release.py
STALE_PATTERNS = [
    (r"(?<![`\"])\b37[ -]+dbt[ -]*models?(?![\`\"])", "37 dbt models"),
    (r"(?<![`\"])\b37[ -]+SQL[ -]*models?(?![\`\"])", "37 SQL models"),
    (r"\b12[ -]+intermediate[ -]*(?:views?|models?)\b", "12 intermediate"),
    (r"[Ii]ntermediate\s*\(12\)", "Intermediate (12)"),
    (r"\b18[ -]+analytics[ -]+marts?\b", "18 analytics marts"),
    (r"\b18[ -]+mart[ -]*models?\b", "18 mart models"),
    (r"[Mm]arts?\s*\(18\)", "Marts (18)"),
    (r"226\+[ -]*(pytest|tests?)", "226+ pytest/tests"),
    (r"34[ -]+Python[ -]+test[ -]*files?", "34 Python test files"),
    (r"Phase\s+3[ ·-]*Streamlit", "Phase 3 Streamlit"),
    (r"F:[/\\]RAG[/\\]", "local path F:/RAG/"),
    (r"C:\\Users\\", "local path C:\\Users\\"),
]


def _match_label(patterns, text):
    hits = []
    for pat, label in patterns:
        if re.search(pat, text):
            hits.append(label)
    return hits


class TestStalePatterns:
    def test_rejects_37_dbt_models(self):
        assert _match_label(STALE_PATTERNS, "37 dbt models across layers")

    def test_rejects_18_analytics_marts(self):
        assert _match_label(STALE_PATTERNS, "with 18 analytics marts")

    def test_allows_18_interactive_filters(self):
        assert not _match_label(STALE_PATTERNS, "18 interactive filters")

    def test_rejects_12_intermediate(self):
        assert _match_label(STALE_PATTERNS, "12 intermediate models")

    def test_rejects_226_plus_pytest(self):
        assert _match_label(STALE_PATTERNS, "226+ pytest tests")

    def test_rejects_34_python_test_files(self):
        assert _match_label(STALE_PATTERNS, "34 Python test files")

    def test_rejects_phase3_streamlit(self):
        assert _match_label(STALE_PATTERNS, "Phase 3 Streamlit Analytics Dashboard")

    def test_rejects_svg_37_dbt(self):
        assert _match_label(STALE_PATTERNS, "<text>37 dbt models</text>")

    def test_rejects_svg_12_intermediate(self):
        assert _match_label(STALE_PATTERNS, "<text>12 intermediate models</text>")


class TestCurrentFactsPass:
    def test_41_dbt_not_flagged(self):
        assert not _match_label(STALE_PATTERNS, "41 dbt models")

    def test_13_intermediate_not_flagged(self):
        assert not _match_label(STALE_PATTERNS, "13 intermediate models")

    def test_21_marts_not_flagged(self):
        assert not _match_label(STALE_PATTERNS, "21 marts")

    def test_44_dbt_tests_not_flagged(self):
        assert not _match_label(STALE_PATTERNS, "44 dbt tests")

    def test_8_pages_not_flagged(self):
        assert not _match_label(STALE_PATTERNS, "8 Streamlit pages")
