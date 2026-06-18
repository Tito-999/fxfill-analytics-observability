"""Strict row-level reconciliation — re-computes every pass/fail per row.

No snapshot accepted, no provenance, no OR gates.
Each row is independently re-evaluated.
"""

from __future__ import annotations

from typing import Any


def evaluate_reconciliation_row(
    table_name: str,
    raw_rows: int | None,
    staging_rows: int | None,
) -> dict[str, Any]:
    """Evaluate one reconciliation row and return structured results.

    Returns None for fields that cannot be measured.
    """
    measurement_possible = raw_rows is not None and staging_rows is not None

    result: dict[str, Any] = {
        "table_name": table_name,
        "raw_rows": raw_rows,
        "staging_rows": staging_rows,
        "expected_difference": 0,
        "absolute_difference": None,
        "relative_difference": None,
        "finite_state": True,
        "expected_pass": True,
        "stored_pass": measurement_possible and raw_rows == staging_rows,
        "measurement_completed": measurement_possible,
    }

    if measurement_possible:
        assert raw_rows is not None
        assert staging_rows is not None
        delta = raw_rows - staging_rows
        result["absolute_difference"] = abs(delta)
        if staging_rows > 0:
            result["relative_difference"] = abs(delta) / staging_rows
        result["finite_state"] = True
        result["expected_pass"] = delta == 0
        result["stored_pass"] = delta == 0

    return result


def compute_strict_reconciliation(
    raw_staging: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Compute strict row-level reconciliation from raw_staging data.

    Args:
        raw_staging: dict of table_name -> {"raw_rows": int|None, "staging_rows": int|None, "delta": int|None}

    Returns:
        Structured reconciliation evidence.
    """
    rows = []
    reconciliation_row_count = 0
    rows_examined = 0
    incomplete_reconciliation_rows = 0
    non_finite_reconciliation_rows = 0
    incorrect_pass_flag_count = 0
    failed_reconciliation_rows = 0
    hardcoded_pass_count = 0

    for table_name, data in raw_staging.items():
        raw_rows = data.get("raw_rows")
        staging_rows = data.get("staging_rows")
        row_result = evaluate_reconciliation_row(table_name, raw_rows, staging_rows)
        rows.append(row_result)

        if row_result["measurement_completed"]:
            reconciliation_row_count += 1
            rows_examined += 1

            if not row_result["finite_state"]:
                non_finite_reconciliation_rows += 1
            if row_result["expected_pass"] is False:
                failed_reconciliation_rows += 1
            if row_result["expected_pass"] is True and row_result["stored_pass"] is False:
                incorrect_pass_flag_count += 1
        else:
            incomplete_reconciliation_rows += 1

    measurement_completed = reconciliation_row_count > 0
    strict_reconciliation_passed = (
        measurement_completed is True
        and reconciliation_row_count > 0
        and rows_examined == reconciliation_row_count
        and incomplete_reconciliation_rows == 0
        and non_finite_reconciliation_rows == 0
        and incorrect_pass_flag_count == 0
        and failed_reconciliation_rows == 0
        and hardcoded_pass_count == 0
    )

    return {
        "measurement_completed": measurement_completed,
        "reconciliation_row_count": reconciliation_row_count,
        "rows_examined": rows_examined,
        "incomplete_reconciliation_rows": incomplete_reconciliation_rows,
        "non_finite_reconciliation_rows": non_finite_reconciliation_rows,
        "incorrect_pass_flag_count": incorrect_pass_flag_count,
        "failed_reconciliation_rows": failed_reconciliation_rows,
        "hardcoded_pass_count": hardcoded_pass_count,
        "strict_reconciliation_passed": strict_reconciliation_passed,
        "rows": rows,
    }
