"""
Quality report generation that orchestrates Pandera schema validation
and cross-table business rule checks.

Produces:
- data_quality_summary.json
- data_quality_failures.parquet
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from fxfill_analytics.quality.checks import run_all_checks
from fxfill_analytics.quality.schemas import SCHEMA_REGISTRY


def _strip_tz(df: pd.DataFrame) -> pd.DataFrame:
    """Convert timezone-aware datetime columns to tz-naive for Pandera validation."""
    result = df.copy()
    for col in result.columns:
        if result[col].dtype.name.startswith("datetime64"):
            # Check if timezone-aware
            if hasattr(result[col].dtype, "tz") and result[col].dtype.tz is not None:
                result[col] = result[col].dt.tz_localize(None)
    return result


def validate_schemas(
    tables: dict[str, pd.DataFrame],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Validate each table against its Pandera schema.

    Args:
        tables: Dict mapping table name to DataFrame.

    Returns:
        Tuple of (schema_report dict, schema_failures list).
    """
    schema_results: dict[str, dict[str, Any]] = {}
    all_failures: list[dict[str, Any]] = []

    for name, schema_cls in SCHEMA_REGISTRY.items():
        df = tables.get(name)
        if df is None:
            schema_results[name] = {"status": "skipped", "reason": "table not found"}
            continue

        # Strip timezone for Pandera validation compatibility
        df_validated = _strip_tz(df)

        try:
            schema_cls.validate(df_validated, lazy=True)
            schema_results[name] = {"status": "passed", "failures": 0}
        except Exception as exc:
            err_str = str(exc)
            # Count schema errors from lazy validation
            error_count = err_str.count("SchemaError") if "SchemaError" in err_str else 1
            schema_results[name] = {
                "status": "failed" if error_count > 0 else "warning",
                "failures": error_count,
                "error_summary": err_str[:500],
            }

            # Record as failures
            if error_count > 0:
                all_failures.append(
                    {
                        "check_id": f"SCHEMA-{name}",
                        "check_name": f"Pandera schema validation: {name}",
                        "severity": "FATAL" if "column" in err_str.lower() else "WARNING",
                        "table_name": name,
                        "record_id": "schema_level",
                        "failure_reason": err_str[:300],
                        "expected_anomaly": False,
                        "phenomenon_id": None,
                        "detected_at": datetime.now(UTC).isoformat(),
                    }
                )

    return schema_results, all_failures


def generate_quality_report(
    tables: dict[str, pd.DataFrame],
    output_dir: Path,
    manifest: dict[str, Any] | None = None,
    phenomena_enabled: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """
    Run full quality validation and write reports.

    Args:
        tables: Dict mapping table name to DataFrame.
        output_dir: Directory to write quality reports to.
        manifest: Generation manifest to enrich the quality summary.
        phenomena_enabled: Dict mapping phenomenon_id to enabled flag.

    Returns:
        Quality summary dict.
    """
    started_at = datetime.now(UTC)

    # ── Step 1: Schema validation ──
    schema_results, schema_failures = validate_schemas(tables)

    # ── Step 2: Cross-table checks ──
    cross_table_failures, checks_summary = run_all_checks(tables, phenomena_enabled)

    # ── Step 3: Combine failures ──
    all_failures = schema_failures + cross_table_failures

    # ── Step 4: Build per-table summaries ──
    table_summaries: dict[str, dict[str, Any]] = {}
    for name, df in tables.items():
        table_summaries[name] = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "schema_status": schema_results.get(name, {}).get("status", "not_checked"),
        }

    finished_at = datetime.now(UTC)

    # ── Step 5: Overall status ──
    fatal_count = sum(1 for f in all_failures if f["severity"] == "FATAL")
    warning_count = sum(1 for f in all_failures if f["severity"] == "WARNING")
    expected_anomalies = sum(1 for f in all_failures if f["expected_anomaly"])

    if fatal_count == 0 and warning_count == 0:
        overall = "passed"
    elif fatal_count == 0:
        overall = "warnings"
    else:
        overall = "failed"

    summary: dict[str, Any] = {
        "run_id": manifest.get("run_id", "unknown") if manifest else "unknown",
        "seed": manifest.get("seed") if manifest else None,
        "config_hash": manifest.get("config_hash") if manifest else None,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "overall_status": overall,
        "checks_total": checks_summary["checks_total"] + len(SCHEMA_REGISTRY),
        "checks_passed": checks_summary["checks_passed"]
        + sum(1 for v in schema_results.values() if v.get("status") == "passed"),
        "checks_warned": warning_count,
        "checks_failed": fatal_count,
        "expected_anomalies_detected": expected_anomalies,
        "unexpected_failures": len(all_failures) - expected_anomalies,
        "table_summaries": table_summaries,
    }

    # ── Write outputs ──
    with open(output_dir / "data_quality_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str, ensure_ascii=False)

    if all_failures:
        failures_df = pd.DataFrame(all_failures)
        failures_df.to_parquet(output_dir / "data_quality_failures.parquet", index=False)
    else:
        # Write empty failures file
        pd.DataFrame(
            columns=[
                "check_id",
                "check_name",
                "severity",
                "table_name",
                "record_id",
                "failure_reason",
                "expected_anomaly",
                "phenomenon_id",
                "detected_at",
            ]
        ).to_parquet(output_dir / "data_quality_failures.parquet", index=False)

    return summary
