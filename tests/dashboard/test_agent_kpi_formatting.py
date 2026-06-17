"""Verify Agent KPI cards use explicit format types."""

from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent.parent


def test_agent_page_has_explicit_latency_format():
    page = PROJECT / "dashboard" / "pages" / "4_Agent_Observability.py"
    content = page.read_text(encoding="utf-8")
    assert '"format_type": "latency_ms"' in content, "Agent page missing latency_ms format"


def test_agent_page_has_explicit_percent_format():
    page = PROJECT / "dashboard" / "pages" / "4_Agent_Observability.py"
    content = page.read_text(encoding="utf-8")
    assert '"format_type": "percent"' in content, "Agent page missing percent format"


def test_agent_page_has_explicit_currency_format():
    page = PROJECT / "dashboard" / "pages" / "4_Agent_Observability.py"
    content = page.read_text(encoding="utf-8")
    assert '"format_type": "currency"' in content, "Agent page missing currency format"


def test_agent_page_has_explicit_integer_format():
    page = PROJECT / "dashboard" / "pages" / "4_Agent_Observability.py"
    content = page.read_text(encoding="utf-8")
    assert '"format_type": "integer"' in content, "Agent page missing integer format"
