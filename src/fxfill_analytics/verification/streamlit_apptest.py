"""Shared Streamlit AppTest utilities for acceptance verification.

All dashboard truthfulness and test modules use these functions
so acceptance logic and test logic never drift.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent.parent.parent


@dataclass
class AppTestResult:
    page_name: str = ""
    exception_count: int = 0
    exception_messages: list[str] = field(default_factory=list)
    metric_values: dict[str, str] = field(default_factory=dict)
    visible_strings: list[str] = field(default_factory=list)
    dataframe_values: list[str] = field(default_factory=list)


def _setup_env(database_path: Path) -> dict:
    env = {
        "FXFILL_DUCKDB_PATH": str(database_path),
        "PYTHONNOUSERSITE": "1",
        "NO_PROXY": "127.0.0.1,localhost",
        "no_proxy": "127.0.0.1,localhost",
        "PYTHONPATH": str(PROJECT),
    }
    for k, v in env.items():
        os.environ[k] = v
    return env


def _clear_cache():
    try:
        from dashboard.services.database import get_connection

        get_connection.clear()
    except Exception:
        pass


def run_streamlit_page(
    page_path: Path,
    database_path: Path,
    timeout_seconds: int = 90,
) -> AppTestResult:
    """Run a Streamlit page with real database and collect visible content."""
    _setup_env(database_path)
    _clear_cache()
    sys.path.insert(0, str(PROJECT))

    from streamlit.testing.v1 import AppTest

    try:
        app = AppTest.from_file(str(page_path))
        app.run(timeout=timeout_seconds)
    except Exception as e:
        result = AppTestResult(
            page_name=page_path.name, exception_count=1, exception_messages=[str(e)[:200]]
        )
        _clear_cache()
        return result

    result = AppTestResult(page_name=page_path.name, exception_count=len(app.exception))

    if app.exception:
        result.exception_messages = [str(e.value)[:200] for e in app.exception]

    result.metric_values = _collect_metric_values(app)
    result.visible_strings = _collect_visible_strings(app)
    result.dataframe_values = _collect_dataframe_strings(app)

    _clear_cache()
    return result


def _collect_metric_values(app) -> dict[str, str]:
    metrics = {}  # type: ignore[var-annotated]  # pre-existing: missing type annotation
    if hasattr(app, "root"):
        try:
            for el in app.root.children:
                _recurse_metrics(el, metrics)
        except Exception:
            pass
    return metrics


def _recurse_metrics(el, metrics: dict):
    el_type = type(el).__name__ if hasattr(el, "__class__") else ""
    if "Metric" in el_type:
        try:
            label = getattr(el, "label", "")
            value = getattr(el, "value", "")
            if label and value:
                metrics[str(label)] = str(value)
        except Exception:
            pass
    if hasattr(el, "children"):
        try:
            for child in el.children:
                _recurse_metrics(child, metrics)
        except Exception:
            pass


def _collect_visible_strings(app) -> list[str]:
    strings = []  # type: ignore[var-annotated]  # pre-existing: missing type annotation
    element_types = ["Markdown", "Text", "Caption", "Title", "Info", "Warning", "Error", "Success"]
    try:
        if hasattr(app, "root"):
            for el in app.root.children:
                _recurse_strings(el, element_types, strings)
    except Exception:
        pass
    return strings


def _recurse_strings(el, element_types: list[str], strings: list):
    el_type = type(el).__name__ if hasattr(el, "__class__") else ""
    if any(t in el_type for t in element_types):
        for attr in ("value", "body", "text"):
            v = getattr(el, attr, None)
            if isinstance(v, str) and v.strip():
                strings.append(v)
    if hasattr(el, "children"):
        try:
            for child in el.children:
                _recurse_strings(child, element_types, strings)
        except Exception:
            pass


def _collect_dataframe_strings(app) -> list[str]:
    strings = []  # type: ignore[var-annotated]  # pre-existing: missing type annotation
    try:
        if hasattr(app, "root"):
            for el in app.root.children:
                _recurse_df(el, strings)
    except Exception:
        pass
    return strings


def _recurse_df(el, strings: list):
    el_type = type(el).__name__ if hasattr(el, "__class__") else ""
    if "DataFrame" in el_type or "Table" in el_type:
        try:
            body = getattr(el, "value", None)
            if isinstance(body, str):
                strings.append(body)
        except Exception:
            pass
    if hasattr(el, "children"):
        try:
            for child in el.children:
                _recurse_df(child, strings)
        except Exception:
            pass


def collect_all_visible_text(result: AppTestResult) -> str:
    """Combine all visible text from a page run into one string for pattern matching."""
    parts = []  # type: ignore[var-annotated]  # pre-existing: missing type annotation
    parts.extend(result.metric_values.values())
    parts.extend(result.visible_strings)
    parts.extend(result.dataframe_values)
    return " ".join(parts)
