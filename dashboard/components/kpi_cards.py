"""KPI card component with explicit format types for Streamlit dashboard."""

import math
from typing import Literal

import streamlit as st

FormatType = Literal["auto", "integer", "decimal", "percent", "currency", "latency_ms"]


def format_kpi_value(value, format_type: FormatType = "auto") -> str:
    """Format a KPI value according to its explicit type.

    Rules:
        None, NaN, +inf, -inf → "N/A"
        percent → 1.8%
        currency → $0.0359
        latency_ms → 11,575 ms
        integer → 3,565
        decimal → 41.2
        auto → legacy heuristic (string-based guessing)
    """
    # ── Sentinel values (None, NaN, Inf) always return N/A ──
    if value is None:
        return "N/A"
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return "N/A"

    if format_type == "percent":
        return f"{float(value):.1%}"
    elif format_type == "currency":
        return f"${float(value):,.4f}"
    elif format_type == "latency_ms":
        return f"{float(value):,.0f} ms"
    elif format_type == "integer":
        if isinstance(value, float) and value == int(value):
            return f"{int(value):,}"
        return f"{int(value):,}"
    elif format_type == "decimal":
        return f"{float(value):,.1f}"
    elif format_type == "auto":
        # Legacy heuristic
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return "N/A"
            return f"{value:,.1f}"
        elif isinstance(value, int) and value > 999:
            return f"{value:,}"
        return str(value)
    else:
        return str(value)


def kpi_card(
    label: str,
    value,
    delta=None,
    help_text: str = "",
    delta_color: str = "normal",
    format_type: FormatType = "auto",
) -> None:
    """Render a single KPI metric card."""
    formatted_value = format_kpi_value(value, format_type)

    st.metric(
        label=label,
        value=formatted_value,
        delta=delta,
        delta_color=delta_color,  # type: ignore[arg-type]
        help=help_text or f"Metric: {label}",
    )


def kpi_row(cards: list[dict], cols: int = 4):
    """Render a row of KPI cards.

    Each card dict supports:
        label: str
        value: number | None
        format_type: one of auto|integer|decimal|percent|currency|latency_ms
        delta: optional delta
        help: optional tooltip
        delta_color: optional delta colour
    """
    columns = st.columns(cols)
    for i, card in enumerate(cards):
        with columns[i % cols]:
            kpi_card(
                label=card.get("label", ""),
                value=card.get("value", 0),
                delta=card.get("delta"),
                help_text=card.get("help", ""),
                delta_color=card.get("delta_color", "normal"),
                format_type=card.get("format_type", "auto"),
            )
