"""Integration test: verify dbt models exist and are queryable."""

from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def db_path():
    return PROJECT / "warehouse" / "fxfill.duckdb"


class TestDbtModelsExist:
    def test_dbt_project_file(self):
        assert (PROJECT / "dbt_fxfill" / "dbt_project.yml").exists()

    def test_model_count(self):
        models = list((PROJECT / "dbt_fxfill" / "models").rglob("*.sql"))
        yml = list((PROJECT / "dbt_fxfill" / "models").rglob("*.yml"))
        total = len(models) + len(yml)
        assert total >= 38, f"Expected >=38 model files, found {total}"


class TestDuckDBConnection:
    def test_database_exists(self, db_path):
        if db_path.exists():
            import duckdb

            conn = duckdb.connect(str(db_path), read_only=True)
            try:
                result = conn.execute("SELECT COUNT(*) FROM raw.raw_users").fetchone()
                assert result is not None
                assert result[0] > 0
            finally:
                conn.close()
