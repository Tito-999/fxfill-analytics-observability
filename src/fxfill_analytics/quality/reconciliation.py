"""Strict source-to-warehouse reconciliation with re-computed pass flags.

Every reconciliation row is independently validated against its tolerance.
The original "passed" flag from input data is treated as a stored claim,
never as the source of truth.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReconciliationRow:
    metric_id: str
    metric_name: str
    source_value: float | None
    warehouse_value: float | None
    tolerance: float
    source_definition: str = ""
    warehouse_definition: str = ""


def _is_finite(v: Any) -> bool:
    if v is None:
        return False
    try:
        f = float(v)
        return math.isfinite(f)
    except (ValueError, TypeError):
        return False


def evaluate_reconciliation_row(row: dict | ReconciliationRow) -> dict:
    """Re-compute pass for a single reconciliation row.

    Returns a dict with: metric_id, source_value, warehouse_value,
    absolute_difference, tolerance, stored_passed, recomputed_passed,
    pass_flag_matches, is_complete, is_finite.
    """
    if isinstance(row, dict):
        sid = str(row.get("metric_id", row.get("metric_name", "")))
        sname = str(row.get("metric_name", row.get("metric_id", "")))
        sv = row.get("source_value")
        wv = row.get("warehouse_value")
        tol = row.get("tolerance", 0.0)
        sdef = str(row.get("source_definition", ""))
        wdef = str(row.get("warehouse_definition", ""))
        stored_passed = row.get("passed", None)
        has_stored_passed = "passed" in row
    else:
        sid = row.metric_id
        sname = row.metric_name
        sv = row.source_value
        wv = row.warehouse_value
        tol = row.tolerance
        sdef = row.source_definition
        wdef = row.warehouse_definition
        stored_passed = None
        has_stored_passed = False

    source_ok = _is_finite(sv) and sv is not None
    warehouse_ok = _is_finite(wv) and wv is not None
    tolerance_ok = _is_finite(tol) and tol >= 0
    is_complete = source_ok and warehouse_ok and tolerance_ok
    is_finite_row = all(_is_finite(v) for v in [sv, wv, tol] if v is not None)

    if is_complete:
        abs_diff = abs(float(sv) - float(wv))  # type: ignore[arg-type]  # pre-existing: float() on Any|None
        recomputed = abs_diff <= tol
    else:
        abs_diff = None
        recomputed = False

    pass_flag_matches = None
    if has_stored_passed and is_complete:
        pass_flag_matches = bool(stored_passed) == recomputed

    return {
        "metric_id": sid,
        "metric_name": sname,
        "source_value": sv,
        "warehouse_value": wv,
        "absolute_difference": abs_diff,
        "tolerance": tol,
        "stored_passed": stored_passed if has_stored_passed else None,
        "recomputed_passed": recomputed,
        "pass_flag_matches": pass_flag_matches,
        "is_complete": is_complete,
        "is_finite": is_finite_row,
        "source_definition": sdef,
        "warehouse_definition": wdef,
    }


def validate_reconciliation_rows(rows: Sequence[Mapping[str, object] | dict]) -> dict:
    """Validate a sequence of reconciliation rows.

    Returns a dict with aggregate statistics and accepted flag.
    """
    evaluated = [evaluate_reconciliation_row(r) for r in rows]  # type: ignore[arg-type]  # pre-existing: Mapping vs dict type variance

    row_count = len(evaluated)
    incomplete = sum(1 for r in evaluated if not r["is_complete"])
    non_finite = sum(1 for r in evaluated if not r["is_finite"])
    incorrect_pass = sum(1 for r in evaluated if r["pass_flag_matches"] is False)
    failed_rows = sum(1 for r in evaluated if not r["recomputed_passed"])

    # Hardcoded pass detection: stored_passed=True but row fails re-computation
    hardcoded = sum(
        1
        for r in evaluated
        if r["stored_passed"] is True and (not r["is_complete"] or r["pass_flag_matches"] is False)
    )

    accepted = (
        row_count > 0
        and incomplete == 0
        and non_finite == 0
        and incorrect_pass == 0
        and failed_rows == 0
        and hardcoded == 0
    )

    return {
        "rows": evaluated,
        "row_count": row_count,
        "incomplete_reconciliation_rows": incomplete,
        "non_finite_reconciliation_rows": non_finite,
        "incorrect_pass_flag_count": incorrect_pass,
        "failed_reconciliation_rows": failed_rows,
        "hardcoded_pass_count": hardcoded,
        "accepted": accepted,
    }
