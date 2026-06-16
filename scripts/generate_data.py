"""
CLI entry point for synthetic data generation.

Usage:
    python scripts/generate_data.py --size medium --seed 20260616
"""

import argparse
import sys
from pathlib import Path

# Ensure project source is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic FxFill data.")
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
    args = parser.parse_args()

    print(f"[generate_data] Size={args.size}, Seed={args.seed}")
    print("[generate_data] NOT YET IMPLEMENTED — Phase 1")
    sys.exit(0)


if __name__ == "__main__":
    main()
