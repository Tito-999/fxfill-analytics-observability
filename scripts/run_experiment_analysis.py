"""CLI for Phase 4 statistical experiment analysis."""
import argparse, json, sys, time, os
from datetime import UTC, datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "src"))


def main():
    p = argparse.ArgumentParser(description="Run formal A/B experiment analysis")
    p.add_argument("--experiment", default="validation_before_autofill_v1")
    p.add_argument("--database", default="warehouse/fxfill.duckdb")
    p.add_argument("--config", default="configs/experiments/validation_before_autofill_v1.yaml")
    p.add_argument("--output-dir", default="reports/phase4")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--bootstrap-iterations", type=int, default=None)
    p.add_argument("--seed", type=int, default=20260616)
    p.add_argument("--population", default="clean_itt")
    p.add_argument("--skip-figures", action="store_true")
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args()

    db_path = Path(args.database)
    if not db_path.is_absolute():
        db_path = PROJECT / db_path
    if not db_path.exists():
        print(f"ERROR: Database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir)
    if not out_dir.is_absolute():
        out_dir = PROJECT / out_dir
    if out_dir.exists() and not args.overwrite:
        print(f"ERROR: Output dir exists: {out_dir}. Use --overwrite.", file=sys.stderr)
        sys.exit(1)
    out_dir.mkdir(parents=True, exist_ok=True)

    os.environ["FXFILL_DUCKDB_PATH"] = str(db_path)
    import duckdb
    from fxfill_analytics.experimentation.report import generate_report
    from fxfill_analytics.experimentation.config import load_experiment_config

    cfg = load_experiment_config(args.experiment)
    if args.bootstrap_iterations:
        cfg["bootstrap_iterations"] = args.bootstrap_iterations
    cfg["bootstrap_seed"] = args.seed

    conn = duckdb.connect(str(db_path), read_only=True)
    t0 = time.perf_counter()
    print(f"Running experiment analysis: {args.experiment}")
    report = generate_report(args.experiment, conn)
    elapsed = time.perf_counter() - t0
    report["performance"] = {"total_duration_seconds": round(elapsed, 1), "peak_memory_mb": "see_diagnostic"}
    conn.close()

    with open(out_dir / "experiment_analysis.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    md = [f"# Experiment Analysis: {args.experiment}\n", f"Generated: {datetime.now(UTC).isoformat()}\n",
          f"Duration: {elapsed:.1f}s\n", f"\n## Primary Metric\n",
          f"A users: {report.get('primary',{}).get('a_n','?')}, B users: {report.get('primary',{}).get('b_n','?')}\n",
          f"Effect: {report.get('primary',{}).get('effect','?')}\n",
          f"Decision: **{report.get('decision',{}).get('recommendation','?')}**\n",
          f"\n*Synthetic data experiment — not a real production result.*\n"]
    with open(out_dir / "experiment_analysis.md", "w") as f:
        f.write("".join(md))
    print(f"Analysis complete: {elapsed:.1f}s. Report: {out_dir}/experiment_analysis.json")


if __name__ == "__main__":
    main()
