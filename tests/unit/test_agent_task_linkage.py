"""Verify agent/product task foreign-key integrity."""

import os
import sys
from pathlib import Path

import duckdb
import pytest

PROJECT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "src"))

DB_PATH = os.environ.get("FXFILL_DUCKDB_PATH", str(PROJECT / "warehouse" / "fxfill.duckdb"))


@pytest.fixture(scope="module")
def conn():
    if not Path(DB_PATH).exists():
        pytest.skip("Database not found")
    c = duckdb.connect(DB_PATH, read_only=True)
    yield c
    c.close()


def test_all_agent_tasks_exist_in_product_events(conn):
    """Every agent_run.task_id must exist in product events."""
    orphaned = conn.execute(
        """
        SELECT COUNT(DISTINCT ar.task_id)
        FROM main_staging.stg_agent_runs ar
        WHERE ar.task_id NOT IN (
            SELECT DISTINCT task_id FROM main_staging.stg_product_events
        )
    """
    ).fetchone()[0]
    assert orphaned == 0, f"{orphaned} agent tasks have no matching product task"


def test_agent_user_id_matches_task_user_id(conn):
    """Agent run user_id must match product event user_id for the same task."""
    mismatches = conn.execute(
        """
        SELECT COUNT(DISTINCT ar.task_id)
        FROM main_staging.stg_agent_runs ar
        INNER JOIN (
            SELECT DISTINCT task_id, user_id FROM main_staging.stg_product_events
        ) pe ON ar.task_id = pe.task_id
        WHERE ar.user_id != pe.user_id
    """
    ).fetchone()[0]
    assert mismatches == 0, f"{mismatches} agent runs have user_id mismatch"


def test_agent_document_id_matches_task_document_id(conn):
    """Agent run document_id must match product event document_id for the same task."""
    mismatches = conn.execute(
        """
        SELECT COUNT(DISTINCT ar.task_id)
        FROM main_staging.stg_agent_runs ar
        INNER JOIN (
            SELECT DISTINCT task_id, document_id FROM main_staging.stg_product_events
        ) pe ON ar.task_id = pe.task_id
        WHERE ar.document_id != pe.document_id
    """
    ).fetchone()[0]
    assert mismatches == 0, f"{mismatches} agent runs have document_id mismatch"


def test_default_preset_every_product_task_has_agent_run(conn):
    """Every product task (with experiment group A or B) should have at least one agent run."""
    unmatched = conn.execute(
        """
        SELECT COUNT(DISTINCT pe.task_id)
        FROM main_staging.stg_product_events pe
        WHERE pe.experiment_group IN ('A', 'B')
          AND pe.task_id NOT IN (
              SELECT DISTINCT task_id FROM main_staging.stg_agent_runs
          )
    """
    ).fetchone()[0]
    assert unmatched == 0, f"{unmatched} experiment tasks have no agent run"


def test_agent_run_id_unique(conn):
    """agent_run_id must be unique."""
    dupes = conn.execute(
        """
        SELECT agent_run_id, COUNT(*) as cnt
        FROM main_staging.stg_agent_runs
        GROUP BY agent_run_id
        HAVING COUNT(*) > 1
    """
    ).fetchall()
    assert len(dupes) == 0, f"Duplicate agent_run_ids found: {dupes[:5]}"
