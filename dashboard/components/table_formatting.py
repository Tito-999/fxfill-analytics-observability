"""Reusable safe table formatters — never display NaN/None/$nan in tables."""

import math

import pandas as pd


def format_optional_number(value, fmt_spec: str = ",.1f") -> str:
    """Format a number, returning N/A for None/NaN/Inf."""
    if value is None:
        return "N/A"
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return "N/A"
        return format(int(v) if v == int(v) else v, fmt_spec)
    except (ValueError, TypeError):
        return "N/A"


def format_optional_currency(value) -> str:
    """Format as USD, returning N/A for None/NaN/Inf."""
    if value is None:
        return "N/A"
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return "N/A"
        return f"${v:,.4f}"
    except (ValueError, TypeError):
        return "N/A"


def format_optional_integer(value) -> str:
    """Format as integer, returning N/A for None/NaN/Inf."""
    if value is None:
        return "N/A"
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return "N/A"
        return f"{int(v):,}"
    except (ValueError, TypeError):
        return "N/A"


def format_dataframe_for_display(
    df: pd.DataFrame,
    column_formats: dict[str, str],
) -> pd.DataFrame:
    """Apply safe formatters to specified columns in place.

    *column_formats* maps column name → format type:
        "number", "currency", "integer", "percent"
    """
    result = df.copy()
    for col, fmt in column_formats.items():
        if col not in result.columns:
            continue
        if fmt == "currency":
            result[col] = result[col].apply(format_optional_currency)
        elif fmt == "integer":
            result[col] = result[col].apply(format_optional_integer)
        elif fmt == "percent":
            result[col] = result[col].apply(
                lambda v: (
                    f"{v:.1%}"
                    if pd.notna(v)
                    and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))
                    else "N/A"
                )
            )
        elif fmt == "number":
            result[col] = result[col].apply(format_optional_number)
    return result
