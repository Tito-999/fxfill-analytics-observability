"""Streamlit AppTest for the three remaining business pages."""

import os
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT))
os.environ["PYTHONPATH"] = str(PROJECT)

DB = os.environ.get("FXFILL_DUCKDB_PATH", str(PROJECT / "warehouse" / "fxfill.duckdb"))

PAGES = [
    "dashboard/pages/3_Feature_Adoption.py",
    "dashboard/pages/4_Agent_Observability.py",
    "dashboard/pages/5_AB_Test.py",
]


@pytest.mark.parametrize("page_path", PAGES)
def test_business_page_renders(page_path: str):
    if not Path(DB).exists():
        pytest.skip("Database not found")

    os.environ["PYTHONNOUSERSITE"] = "1"
    os.environ["NO_PROXY"] = "127.0.0.1,localhost"
    os.environ["no_proxy"] = "127.0.0.1,localhost"
    os.environ["FXFILL_DUCKDB_PATH"] = DB

    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(PROJECT / page_path))
    app.run(timeout=60)

    errors = [str(e.value)[:200] for e in app.exception]
    assert len(app.exception) == 0, f"{Path(page_path).name}: {errors}"
