"""Verify product event terminal state consistency — no export+abandon conflicts."""

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


def test_no_task_both_exported_and_abandoned(conn):
    """A task must not have both form_exported and task_abandoned."""
    conflicts = conn.execute(
        """
        SELECT task_id, MAX(event_name = 'form_exported') AS exported,
               MAX(event_name = 'task_abandoned') AS abandoned
        FROM main_staging.stg_product_events
        WHERE event_name IN ('form_exported', 'task_abandoned')
        GROUP BY task_id
        HAVING exported = 1 AND abandoned = 1
    """
    ).fetchall()
    assert len(conflicts) == 0, f"{len(conflicts)} tasks have both export and abandon"


def test_each_task_at_most_one_terminal_state(conn):
    """Each task should have at most one terminal event (exported, abandoned, or failed)."""
    ambiguous = conn.execute(
        """
        SELECT task_id,
               MAX(CASE WHEN event_name = 'form_exported' THEN 1 ELSE 0 END) AS exported,
               MAX(CASE WHEN event_name = 'task_abandoned' THEN 1 ELSE 0 END) AS abandoned,
               MAX(CASE WHEN event_name = 'agent_run_failed' THEN 1 ELSE 0 END) AS failed
        FROM main_staging.stg_product_events
        WHERE event_name IN ('form_exported', 'task_abandoned', 'agent_run_failed')
        GROUP BY task_id
        HAVING exported + abandoned + failed > 1
    """
    ).fetchall()
    assert len(ambiguous) == 0, f"{len(ambiguous)} tasks have multiple terminal states"


def test_form_exported_after_form_review_started(conn):
    """form_exported must occur after form_review_started."""
    violations = conn.execute(
        """
        WITH ordered AS (
            SELECT task_id, event_name, MIN(event_time) AS first_time
            FROM main_staging.stg_product_events
            WHERE event_name IN ('form_review_started', 'form_exported')
            GROUP BY task_id, event_name
        )
        SELECT r.task_id
        FROM ordered r
        INNER JOIN ordered e ON r.task_id = e.task_id
        WHERE r.event_name = 'form_review_started'
          AND e.event_name = 'form_exported'
          AND r.first_time > e.first_time
    """
    ).fetchall()
    assert len(violations) == 0, f"{len(violations)} tasks have export before review"


def test_abandoned_after_form_review_started(conn):
    """task_abandoned must occur after form_review_started."""
    violations = conn.execute(
        """
        WITH ordered AS (
            SELECT task_id, event_name, MIN(event_time) AS first_time
            FROM main_staging.stg_product_events
            WHERE event_name IN ('form_review_started', 'task_abandoned')
            GROUP BY task_id, event_name
        )
        SELECT r.task_id
        FROM ordered r
        LEFT JOIN ordered a ON r.task_id = a.task_id AND a.event_name = 'task_abandoned'
        WHERE r.event_name = 'form_review_started'
          AND a.task_id IS NOT NULL
          AND r.first_time > a.first_time
    """
    ).fetchall()
    assert len(violations) == 0, f"{len(violations)} tasks have abandon before review"


def test_review_count_exceeds_export_count(conn):
    """Tasks starting review should exceed tasks reaching export."""
    review = conn.execute(
        "SELECT COUNT(DISTINCT task_id) FROM main_staging.stg_product_events WHERE event_name = 'form_review_started'"
    ).fetchone()[0]
    export = conn.execute(
        "SELECT COUNT(DISTINCT task_id) FROM main_staging.stg_product_events WHERE event_name = 'form_exported'"
    ).fetchone()[0]
    abandoned = conn.execute(
        "SELECT COUNT(DISTINCT task_id) FROM main_staging.stg_product_events WHERE event_name = 'task_abandoned'"
    ).fetchone()[0]
    assert review > 0, "No tasks entered review"
    assert export > 0, "No tasks were exported"
    assert abandoned > 0, "No tasks were abandoned"
    assert review > export, f"Review ({review}) should exceed export ({export})"
