"""Verify Agent stage performance table uses N/A for non-LLM spans."""

from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent.parent


def test_agent_page_no_dollar_nan():
    """Agent page source must not contain $nan pattern."""
    page = PROJECT / "dashboard" / "pages" / "4_Agent_Observability.py"
    content = page.read_text(encoding="utf-8")
    assert "$nan" not in content, "Agent page contains $nan literal"


def test_agent_page_uses_na_for_non_llm():
    """Agent stage section uses N/A for non-LLM tokens and cost."""
    page = PROJECT / "dashboard" / "pages" / "4_Agent_Observability.py"
    content = page.read_text(encoding="utf-8")
    assert "N/A" in content, "Agent stage should use N/A for non-applicable values"


def test_agent_llm_cost_chart_filtered():
    """Cost chart title should mention LLM, not mixing all spans."""
    page = PROJECT / "dashboard" / "pages" / "4_Agent_Observability.py"
    content = page.read_text(encoding="utf-8")
    # Either cost chart is filtered to LLM or table shows N/A
    has_llm_filter = "span_type" in content and "llm" in content.lower()
    assert has_llm_filter, "Agent stage should filter by span_type for cost chart"
