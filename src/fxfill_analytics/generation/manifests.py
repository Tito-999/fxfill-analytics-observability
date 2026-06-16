"""
Manifest generation for synthetic data generation runs.

Produces:
- generation_manifest.json: run metadata, table stats, performance
- phenomena_manifest.json: per-phenomenon configuration and observed signals
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def write_manifest(manifest: dict[str, Any], output_dir: Path) -> Path:
    """Write the generation manifest to a JSON file."""
    path = output_dir / "generation_manifest.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str, ensure_ascii=False)
    return path


def build_table_summary(
    name: str,
    df: Any,  # pd.DataFrame
    primary_key: str,
    foreign_keys: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a per-table summary entry for the manifest."""
    columns = list(df.columns)
    return {
        "name": name,
        "row_count": len(df),
        "column_count": len(columns),
        "columns": columns,
        "primary_key": primary_key,
        "foreign_keys": foreign_keys or {},
        "dtypes": {c: str(df[c].dtype) for c in columns},
        "memory_mb": round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2),
    }


def build_phenomena_manifest(
    phenomena_cfg: dict[str, Any],
    observed: dict[str, dict[str, Any]],
    output_dir: Path,
) -> Path:
    """
    Build and write the phenomena manifest.

    Args:
        phenomena_cfg: The phenomena configuration dict.
        observed: Dict mapping phenomenon_id to observed signals.
        output_dir: Directory to write the manifest to.

    Returns:
        Path to the written manifest file.
    """
    entries: list[dict[str, Any]] = []
    for pid, cfg in phenomena_cfg.items():
        if isinstance(cfg, dict) and cfg.get("enabled", False):
            obs = observed.get(pid, {})
            entries.append(
                {
                    "phenomenon_id": pid,
                    "enabled": True,
                    "configured_effect": cfg.get("effect_parameter", cfg),
                    "affected_rows": obs.get("affected_rows"),
                    "affected_date_range": cfg.get("affected_date_range"),
                    "expected_signal": cfg.get("expected_direction"),
                    "observed_signal": obs.get("observed_signal"),
                    "validation_status": obs.get("validation_status", "not_validated"),
                }
            )

    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "phenomena_count": len(entries),
        "phenomena": entries,
    }

    path = output_dir / "phenomena_manifest.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str, ensure_ascii=False)
    return path
