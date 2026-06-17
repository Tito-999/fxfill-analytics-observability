"""KPI card component for Streamlit dashboard."""

import streamlit as st


def kpi_card(label: str, value, delta=None, help_text: str = "", delta_color: str = "normal") -> None:
    """Render a KPI metric card with tooltip and optional delta."""
    formatted_value = value
    if isinstance(value, float):
        if "rate" in label.lower() or "adoption" in label.lower():
            formatted_value = f"{value:.1%}"
        elif "cost" in label.lower() or "usd" in label.lower():
            formatted_value = f"${value:.4f}"
        elif "latency" in label.lower():
            formatted_value = f"{value:,.0f} ms"
        else:
            formatted_value = f"{value:,.1f}"
    elif isinstance(value, int) and value > 999:
        formatted_value = f"{value:,}"

    st.metric(
        label=label,
        value=formatted_value,
        delta=delta,
        delta_color=delta_color,  # type: ignore[arg-type]
        help=help_text or f"Metric: {label}",
    )


def kpi_row(cards: list[dict], cols: int = 4):
    """Render a row of KPI cards. Each card is a dict with label, value, delta, help."""
    columns = st.columns(cols)
    for i, card in enumerate(cards):
        with columns[i % cols]:
            kpi_card(
                label=card.get("label", ""),
                value=card.get("value", 0),
                delta=card.get("delta"),
                help_text=card.get("help", ""),
                delta_color=card.get("delta_color", "normal"),
            )
