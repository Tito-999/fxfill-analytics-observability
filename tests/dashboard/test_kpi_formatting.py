"""Verify KPI format_kpi_value function and explicit format types."""

from dashboard.components.kpi_cards import format_kpi_value


def test_percent():
    assert format_kpi_value(0.018, "percent") == "1.8%"
    assert format_kpi_value(0.0, "percent") == "0.0%"
    assert format_kpi_value(1.0, "percent") == "100.0%"


def test_nan_returns_na():
    assert format_kpi_value(float("nan"), "percent") == "N/A"
    assert format_kpi_value(float("nan"), "currency") == "N/A"
    assert format_kpi_value(float("nan"), "latency_ms") == "N/A"
    assert format_kpi_value(float("nan"), "integer") == "N/A"
    assert format_kpi_value(float("nan"), "auto") == "N/A"


def test_inf_returns_na():
    assert format_kpi_value(float("inf"), "percent") == "N/A"
    assert format_kpi_value(float("-inf"), "currency") == "N/A"


def test_none_returns_na():
    assert format_kpi_value(None, "percent") == "N/A"
    assert format_kpi_value(None, "currency") == "N/A"


def test_latency_ms():
    assert format_kpi_value(11575.2, "latency_ms") == "11,575 ms"
    assert format_kpi_value(0, "latency_ms") == "0 ms"


def test_integer():
    assert format_kpi_value(3565, "integer") == "3,565"
    assert format_kpi_value(0, "integer") == "0"


def test_currency():
    assert format_kpi_value(0.0359, "currency") == "$0.0359"
    assert format_kpi_value(1.50, "currency") == "$1.5000"


def test_decimal():
    assert format_kpi_value(41.2, "decimal") == "41.2"
    assert format_kpi_value(0.0, "decimal") == "0.0"
