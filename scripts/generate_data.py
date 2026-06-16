"""
CLI entry point for synthetic data generation.

Usage:
    python scripts/generate_data.py --size tiny --seed 20260616
    python scripts/generate_data.py --size medium --seed 20260616 --overwrite
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic FxFill Analytics data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/generate_data.py --size tiny --seed 20260616
  python scripts/generate_data.py --size medium --seed 20260616 --overwrite
  python scripts/generate_data.py --size small --output-dir ./my_data --overwrite
""",
    )
    parser.add_argument(
        "--size",
        choices=["tiny", "small", "medium", "large"],
        default="medium",
        help="Data size preset (default: medium)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260616,
        help="Random seed for reproducibility (default: 20260616)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory (default: data/generated/)",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Start date in YYYY-MM-DD format (default: 120 days before end-date)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=120,
        help="Number of days in the date range (default: 120)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite existing output directory",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to custom generation config YAML",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--disable-phenomenon",
        type=str,
        nargs="*",
        default=None,
        help="Phenomenon IDs to disable (space-separated)",
    )
    parser.add_argument(
        "--enable-only-phenomenon",
        type=str,
        nargs="*",
        default=None,
        help="Only enable these phenomenon IDs (space-separated)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print configuration and exit without generating data",
    )

    args = parser.parse_args()

    # ── Resolve paths ──
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root / "src"))

    if args.output_dir:
        output_dir = Path(args.output_dir)
        if not output_dir.is_absolute():
            output_dir = project_root / output_dir
    else:
        output_dir = project_root / "data" / "generated"

    # ── Date range ──
    if args.start_date:
        try:
            end_date = datetime.strptime(args.start_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            print(f"ERROR: Invalid --start-date format: {args.start_date}", file=sys.stderr)
            print("       Expected YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)
    else:
        end_date = datetime(2026, 6, 14, tzinfo=timezone.utc)

    if args.days <= 0:
        print(f"ERROR: --days must be positive, got {args.days}", file=sys.stderr)
        sys.exit(1)

    start_date = end_date - timedelta(days=args.days)

    # ── Import pipeline (lazy, after sys.path setup) ──
    from fxfill_analytics.generation.pipeline import run_pipeline

    if args.dry_run:
        print(f"Configuration (dry-run):")
        print(f"  size:       {args.size}")
        print(f"  seed:       {args.seed}")
        print(f"  output_dir: {output_dir}")
        print(f"  start_date: {start_date.date()}")
        print(f"  end_date:   {end_date.date()}")
        print(f"  days:       {args.days}")
        print(f"  overwrite:  {args.overwrite}")
        print(f"  log_level:  {args.log_level}")
        sys.exit(0)

    print(f"[generate_data] Starting Phase 1 generation")
    print(f"  size={args.size}, seed={args.seed}, days={args.days}")
    print(f"  date range: {start_date.date()} → {end_date.date()}")
    print(f"  output: {output_dir}")

    try:
        manifest = run_pipeline(
            seed=args.seed,
            size=args.size,
            output_dir=output_dir,
            start_date=start_date,
            end_date=end_date,
            overwrite=args.overwrite,
            disable_phenomena=args.disable_phenomenon,
            enable_only_phenomena=args.enable_only_phenomenon,
        )
    except FileExistsError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # ── Print summary ──
    print(f"\n[generate_data] Generation complete!")
    print(f"  Run ID:    {manifest['run_id']}")
    print(f"  Duration:  {manifest['duration_seconds']}s")
    print(f"  Memory:    {manifest['peak_memory_mb']} MB")
    print(f"  Output:    {manifest['output_size_mb']} MB")
    print(f"  Tables:")
    for t in manifest["tables"]:
        print(f"    {t['name']:30s} → {t['actual_rows']:>10,} rows  (target: {t['configured_target']:>10,})")
    print(f"  Quality:   {manifest['quality_status']}")
    print(f"\n  Output directory: {output_dir / manifest['run_id']}")

    sys.exit(0)


if __name__ == "__main__":
    main()
