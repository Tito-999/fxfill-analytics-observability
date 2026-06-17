"""
Orchestration pipeline for synthetic data generation.

Coordinates all generators in dependency order, handles atomic output,
and produces the generation manifest.
"""

import hashlib
import json
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fxfill_analytics.generation.generate_agent_traces import (
    generate_agent_runs,
    generate_agent_spans,
)
from fxfill_analytics.generation.generate_documents import generate_documents
from fxfill_analytics.generation.generate_experiment_data import (
    generate_experiment_assignments,
)
from fxfill_analytics.generation.generate_product_events import (
    generate_product_events,
)
from fxfill_analytics.generation.generate_sessions import generate_sessions
from fxfill_analytics.generation.generate_users import generate_users

# ── Size presets (number of entities to generate) ──
SIZE_PRESETS: dict[str, dict[str, int]] = {
    "tiny": {
        "users": 200,
        "sessions": 600,
        "documents": 800,
        "events": 4000,
        "agent_runs": 800,
        "agent_spans": 3000,
        "experiment_users": 120,
    },
    "small": {
        "users": 2000,
        "sessions": 6000,
        "documents": 8000,
        "events": 40000,
        "agent_runs": 8000,
        "agent_spans": 30000,
        "experiment_users": 1200,
    },
    "medium": {
        "users": 20000,
        "sessions": 60000,
        "documents": 80000,
        "events": 400000,
        "agent_runs": 80000,
        "agent_spans": 300000,
        "experiment_users": 12000,
    },
    "large": {
        "users": 100000,
        "sessions": 300000,
        "documents": 400000,
        "events": 2000000,
        "agent_runs": 400000,
        "agent_spans": 1500000,
        "experiment_users": 60000,
    },
}


def _try_git_commit() -> str:
    """Return the current git commit hash, or 'unknown'."""
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _config_hash(config: dict[str, Any]) -> str:
    """Stable hash of a configuration dict."""
    raw = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def _get_pk(table_name: str) -> str:
    """Return the primary key column name for a table."""
    pk_map = {
        "users": "user_id",
        "documents": "document_id",
        "sessions": "session_id",
        "product_events": "event_id",
        "agent_runs": "agent_run_id",
        "agent_spans": "span_id",
        "experiment_assignments": "assignment_id",
    }
    return pk_map.get(table_name, "")


def _get_peak_memory_mb() -> float:
    """Best-effort peak memory in MB (Windows). Returns 0.0 if unavailable."""
    try:
        import psutil

        proc = psutil.Process()
        mem_bytes: int = proc.memory_info().peak_wset
        return float(mem_bytes) / (1024.0 * 1024.0)
    except Exception:
        return 0.0


def run_pipeline(
    seed: int,
    size: str,
    output_dir: Path,
    start_date: datetime,
    end_date: datetime,
    *,
    overwrite: bool = False,
    phenomena_config: dict[str, Any] | None = None,
    disable_phenomena: list[str] | None = None,
    enable_only_phenomena: list[str] | None = None,
) -> dict[str, Any]:
    """
    Execute the full synthetic data generation pipeline.

    Args:
        seed: Random seed for reproducibility.
        size: Size preset key ('tiny', 'small', 'medium', 'large').
        output_dir: Target directory for output files.
        start_date: Earliest timestamp in generated data.
        end_date: Latest timestamp in generated data.
        overwrite: If True, overwrite existing output directory.
        phenomena_config: Optional phenomena configuration dict.
        disable_phenomena: Phenomenon IDs to disable.
        enable_only_phenomena: If set, only enable these phenomenon IDs.

    Returns:
        Generation manifest as a dict.

    Raises:
        FileExistsError: If output_dir exists and overwrite=False.
        ValueError: If size is not a valid preset.
    """
    if size not in SIZE_PRESETS:
        raise ValueError(f"Unknown size '{size}'. Choose from: {list(SIZE_PRESETS)}")

    cfg = SIZE_PRESETS[size]
    started_at = datetime.now(UTC)
    table_timings: dict[str, float] = {}

    # ── Resolve output directory ──
    config_hash_val = _config_hash({"seed": seed, "size": size})
    run_name = f"run_{size}_{seed}_{config_hash_val}"
    run_dir = output_dir / run_name

    if run_dir.exists():
        if not overwrite:
            raise FileExistsError(
                f"Output directory already exists: {run_dir}\n" f"Use --overwrite to replace it."
            )
        shutil.rmtree(run_dir)

    # Phase 1: Write to temp directory, then atomically rename
    tmp_dir = output_dir / f".tmp_{run_name}"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ── Independent RNG streams per module (SeedSequence) ──
        ss = np.random.SeedSequence(seed)
        rng_streams = ss.spawn(
            9
        )  # users, docs, sessions, events, runs, spans, exps, phenomena, hash
        rng_u = np.random.default_rng(rng_streams[0])
        rng_d = np.random.default_rng(rng_streams[1])
        rng_s = np.random.default_rng(rng_streams[2])
        rng_e = np.random.default_rng(rng_streams[3])
        rng_ar = np.random.default_rng(rng_streams[4])
        rng_as = np.random.default_rng(rng_streams[5])
        rng_exp = np.random.default_rng(rng_streams[6])
        rng_phen = np.random.default_rng(rng_streams[7])

        # ── Step 1: Users ──
        t0 = time.perf_counter()
        users_df = generate_users(rng_u, cfg["users"], start_date, end_date)
        table_timings["users"] = time.perf_counter() - t0

        user_ids = sorted(users_df["user_id"].tolist())

        # ── Step 2: Documents ──
        t0 = time.perf_counter()
        docs_df = generate_documents(rng_d, cfg["documents"], user_ids, start_date, end_date)
        table_timings["documents"] = time.perf_counter() - t0

        doc_ids = sorted(docs_df["document_id"].tolist())

        # ── Step 3: Sessions ──
        t0 = time.perf_counter()
        sessions_df = generate_sessions(rng_s, cfg["sessions"], user_ids, start_date, end_date)
        table_timings["sessions"] = time.perf_counter() - t0

        session_ids = sorted(sessions_df["session_id"].tolist())

        # ── Step 4: Product Events (with task pipeline) ──
        t0 = time.perf_counter()
        events_df = generate_product_events(
            rng_e,
            cfg["events"],
            user_ids,
            session_ids,
            doc_ids,
            start_date,
            end_date,
            phenomena_config=phenomena_config,
        )
        table_timings["product_events"] = time.perf_counter() - t0

        # ── Step 5: Agent Runs ──
        t0 = time.perf_counter()
        agent_runs_df = generate_agent_runs(
            rng_ar, cfg["agent_runs"], user_ids, doc_ids, start_date, end_date
        )
        table_timings["agent_runs"] = time.perf_counter() - t0

        trace_ids = sorted(agent_runs_df["trace_id"].tolist())

        # ── Step 6: Agent Spans ──
        t0 = time.perf_counter()
        agent_spans_df = generate_agent_spans(
            rng_as, cfg["agent_spans"], trace_ids, start_date, end_date
        )
        table_timings["agent_spans"] = time.perf_counter() - t0

        # ── Step 7: Experiment Assignments ──
        t0 = time.perf_counter()
        experiment_df = generate_experiment_assignments(
            rng_exp, cfg["experiment_users"], user_ids, start_date, end_date
        )
        table_timings["experiment_assignments"] = time.perf_counter() - t0

        # ── Inject phenomena ──
        from fxfill_analytics.generation.phenomena import inject_phenomena

        tables_raw: dict[str, Any] = {
            "users": users_df,
            "documents": docs_df,
            "sessions": sessions_df,
            "product_events": events_df,
            "agent_runs": agent_runs_df,
            "agent_spans": agent_spans_df,
            "experiment_assignments": experiment_df,
        }

        tables, observed_signals = inject_phenomena(
            tables_raw,
            rng_phen,
            end_date,
            phenomena_cfg=phenomena_config,
            disabled_ids=disable_phenomena,
            only_ids=enable_only_phenomena,
        )

        # ── Run quality validation ──
        from fxfill_analytics.quality.quality_report import generate_quality_report

        quality_summary = generate_quality_report(
            tables,
            tmp_dir,
            manifest=None,  # built below
            phenomena_enabled={pid: True for pid in observed_signals},
        )

        # ── Run real phenomena validation ──
        from fxfill_analytics.quality.phenomena_validation import validate_all_phenomena

        validation_results = validate_all_phenomena(tables)

        # ── Write phenomena manifest with real validation data ──
        from fxfill_analytics.generation.manifests import build_phenomena_manifest

        build_phenomena_manifest(phenomena_config or {}, observed_signals, tmp_dir)
        # Also write full validation results
        with open(tmp_dir / "phenomena_validation.json", "w", encoding="utf-8") as f:
            json.dump(validation_results, f, indent=2, default=str, ensure_ascii=False)

        total_size_bytes = 0
        actual_rows: dict[str, int] = {}
        canonical_hashes: dict[str, str] = {}
        for name, df in tables.items():
            path = tmp_dir / f"{name}.parquet"
            df.to_parquet(path, index=False)
            file_size = path.stat().st_size
            total_size_bytes += file_size
            actual_rows[name] = len(df)
            # Compute canonical hash: sort by PK, fixed col order, normalized values
            pk = _get_pk(name)
            df_sorted = (
                df.sort_values(pk).reset_index(drop=True)
                if pk and pk in df.columns
                else df.reset_index(drop=True)
            )
            cols = sorted(df_sorted.columns)
            hasher = hashlib.sha256()
            for c in cols:
                hasher.update(c.encode("utf-8") + b"\x00")
                s = df_sorted[c]
                if hasattr(s.dtype, "tz") and s.dtype.tz is not None:
                    s = s.dt.tz_convert("UTC")
                if s.dtype.name.startswith("datetime"):
                    vals = s.dt.strftime("%Y-%m-%dT%H:%M:%S.%f").fillna("NULL")
                elif s.dtype == bool:
                    vals = s.map({True: "true", False: "false"}).fillna("NULL")
                elif "float" in str(s.dtype):
                    vals = s.apply(lambda x: f"{x:.10f}" if pd.notna(x) else "NULL")
                else:
                    vals = s.fillna("NULL").astype(str)
                hasher.update("\n".join(vals.tolist()).encode("utf-8") + b"\n")
            canonical_hashes[name] = hasher.hexdigest()

        # ── Build manifest ──
        finished_at = datetime.now(UTC)
        duration = (finished_at - started_at).total_seconds()

        # Map table names to config keys
        _table_cfg_map = {
            "users": "users",
            "documents": "documents",
            "sessions": "sessions",
            "product_events": "events",
            "agent_runs": "agent_runs",
            "agent_spans": "agent_spans",
            "experiment_assignments": "experiment_users",
        }
        manifested_tables: list[dict[str, Any]] = []
        for name, cfg_key in _table_cfg_map.items():
            target = cfg.get(cfg_key, 0)
            rows = actual_rows.get(name, 0)
            deviation = (rows - target) / max(target, 1)
            manifested_tables.append(
                {
                    "name": name,
                    "configured_target": target,
                    "actual_rows": rows,
                    "deviation_ratio": round(deviation, 4),
                }
            )

        manifest: dict[str, Any] = {
            "schema_version": "1.0.0",
            "run_id": run_name,
            "synthetic_data": True,
            "seed": seed,
            "size": size,
            "config_hash": config_hash_val,
            "git_commit": _try_git_commit(),
            "python_version": sys.version.split()[0],
            "package_versions": {
                "pandas": __import__("pandas").__version__,
                "numpy": __import__("numpy").__version__,
                "pyarrow": __import__("pyarrow").__version__,
                "duckdb": __import__("duckdb").__version__,
            },
            "start_time": started_at.isoformat(),
            "end_time": finished_at.isoformat(),
            "duration_seconds": round(duration, 2),
            "peak_memory_mb": round(_get_peak_memory_mb(), 2),
            "tables": manifested_tables,
            "table_timings_seconds": {k: round(v, 2) for k, v in table_timings.items()},
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "output_size_bytes": total_size_bytes,
            "output_size_mb": round(total_size_bytes / (1024 * 1024), 2),
            "canonical_table_hashes": canonical_hashes,
            "quality_status": quality_summary["overall_status"],
            "phenomena": phenomena_config if phenomena_config else {},
        }

        # Write manifest in temp dir
        with open(tmp_dir / "generation_manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, default=str, ensure_ascii=False)

        # ── Atomic rename ──
        tmp_dir.rename(run_dir)

        return manifest

    except Exception:
        # Clean up temp directory on failure
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
