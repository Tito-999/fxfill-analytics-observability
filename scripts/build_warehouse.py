"""
CLI entry point for building the DuckDB data warehouse.

Usage:
    python scripts/build_warehouse.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def main() -> None:
    print("[build_warehouse] NOT YET IMPLEMENTED — Phase 2")
    sys.exit(0)


if __name__ == "__main__":
    main()
