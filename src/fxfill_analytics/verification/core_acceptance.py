"""Pure-function Core Release acceptance aggregation.

No subprocess, no filesystem, no database. Receives data, returns derived results.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

GateState = Literal["PASS", "FAIL", "NOT_RUN"]

REQUIRED_GATE_NAMES: tuple[str, ...] = (
    "environment",
    "data_generation",
    "warehouse",
    "dbt_models",
    "dbt_tests",
    "pytest",
    "business_metric_integrity",
    "strict_reconciliation",
    "dashboard_truthfulness",
    "streamlit_smoke",
    "public_audit",
)


def derive_dbt_model_gate(dbt: Mapping[str, Any]) -> tuple[GateState, list[str]]:
    required = [
        "measurement_completed",
        "model_count",
        "model_execution_count",
        "model_success_count",
        "model_fail_count",
        "model_error_count",
        "model_skip_count",
        "model_results_sha256",
        "test_results_sha256",
        "artifacts_paths_distinct",
        "artifacts_hashes_distinct",
        "artifacts_semantically_distinct",
        "artifacts_separated",
        "failures",
    ]
    missing = [f for f in required if f not in dbt or dbt[f] is None]
    if missing:
        return "NOT_RUN", [f"dbt_models.measurement_incomplete:{f}" for f in missing]

    reasons = []
    mc = dbt.get("measurement_completed")
    if mc is not True:
        reasons.append("dbt_models.measurement_completed_not_true")

    if not (isinstance(dbt["model_count"], int) and dbt["model_count"] > 0):
        reasons.append("dbt_models.model_count_invalid")
    if dbt.get("model_execution_count") != dbt.get("model_count"):
        reasons.append("dbt_models.model_execution_count_mismatch")
    if dbt.get("model_success_count") != dbt.get("model_count"):
        reasons.append("dbt_models.model_success_count_mismatch")
    if dbt.get("model_fail_count") != 0:
        reasons.append("dbt_models.model_fail_count_nonzero")
    if dbt.get("model_error_count") != 0:
        reasons.append("dbt_models.model_error_count_nonzero")
    if dbt.get("model_skip_count") != 0:
        reasons.append("dbt_models.model_skip_count_nonzero")

    mr_sha = dbt.get("model_results_sha256")
    tr_sha = dbt.get("test_results_sha256")
    if not (isinstance(mr_sha, str) and len(mr_sha) == 64):
        reasons.append("dbt_models.model_results_sha256_invalid")
    if not (isinstance(tr_sha, str) and len(tr_sha) == 64):
        reasons.append("dbt_models.test_results_sha256_invalid")
    if (
        isinstance(mr_sha, str)
        and isinstance(tr_sha, str)
        and len(mr_sha) == 64
        and len(tr_sha) == 64
        and mr_sha == tr_sha
    ):
        reasons.append("dbt_models.model_test_hashes_equal")

    if dbt.get("artifacts_paths_distinct") is not True:
        reasons.append("dbt_models.artifact_paths_not_distinct")
    if dbt.get("artifacts_hashes_distinct") is not True:
        reasons.append("dbt_models.artifact_hashes_not_distinct")
    if dbt.get("artifacts_semantically_distinct") is not True:
        reasons.append("dbt_models.artifact_semantics_not_distinct")
    if dbt.get("artifacts_separated") is not True:
        reasons.append("dbt_models.artifacts_separated=false")
    if dbt.get("failures") != []:
        reasons.append("dbt_models.embedded_failures_nonempty")

    if reasons:
        return "FAIL", reasons
    return "PASS", []


def derive_dbt_test_gate(dbt: Mapping[str, Any]) -> tuple[GateState, list[str]]:
    required = [
        "measurement_completed",
        "generic_test_count",
        "singular_test_count",
        "test_definition_count",
        "test_execution_count",
        "test_pass",
        "test_fail",
        "test_error",
        "test_skip",
        "test_results_sha256",
        "artifacts_separated",
        "failures",
    ]
    missing = [f for f in required if f not in dbt or dbt[f] is None]
    if missing:
        return "NOT_RUN", [f"dbt_tests.measurement_incomplete:{f}" for f in missing]

    reasons = []
    mc = dbt.get("measurement_completed")
    if mc is not True:
        reasons.append("dbt_tests.measurement_completed_not_true")

    gtc = dbt.get("generic_test_count", 0)
    stc = dbt.get("singular_test_count", 0)
    tdc = dbt.get("test_definition_count", 0)
    tec = dbt.get("test_execution_count", 0)
    tp = dbt.get("test_pass", 0)

    if not (isinstance(gtc, int) and gtc > 0):
        reasons.append("dbt_tests.generic_test_count_invalid")
    if not (isinstance(stc, int) and stc > 0):
        reasons.append("dbt_tests.singular_test_count_invalid")
    if gtc + stc != tdc:
        reasons.append("dbt_tests.test_definition_mismatch")
    if tec != tdc:
        reasons.append("dbt_tests.test_execution_count_mismatch")
    if tp != tdc:
        reasons.append("dbt_tests.test_pass_count_mismatch")
    if dbt.get("test_fail") != 0:
        reasons.append("dbt_tests.test_fail_nonzero")
    if dbt.get("test_error") != 0:
        reasons.append("dbt_tests.test_error_nonzero")
    if dbt.get("test_skip") != 0:
        reasons.append("dbt_tests.test_skip_nonzero")

    tr_sha = dbt.get("test_results_sha256")
    if not (isinstance(tr_sha, str) and len(tr_sha) == 64):
        reasons.append("dbt_tests.test_results_sha256_invalid")
    if dbt.get("artifacts_separated") is not True:
        reasons.append("dbt_tests.artifacts_separated=false")
    if dbt.get("failures") != []:
        reasons.append("dbt_tests.embedded_failures_nonempty")

    if reasons:
        return "FAIL", reasons
    return "PASS", []


def compute_core_acceptance(
    *,
    gates: Mapping[str, GateState],
    failed_gates: Sequence[str],
    warnings: Sequence[str],
) -> dict[str, Any]:
    normalized: dict[str, GateState] = {}
    for name in REQUIRED_GATE_NAMES:
        val = gates.get(name)
        if val in ("PASS", "FAIL", "NOT_RUN"):
            normalized[name] = val
        else:
            normalized[name] = "NOT_RUN"

    not_run_gates = [n for n in REQUIRED_GATE_NAMES if normalized[n] == "NOT_RUN"]
    failed_state_gates = [n for n in REQUIRED_GATE_NAMES if normalized[n] == "FAIL"]
    pass_gates = [n for n in REQUIRED_GATE_NAMES if normalized[n] == "PASS"]

    derived_failed = sorted(set(failed_gates) | set(not_run_gates) | set(failed_state_gates))

    accepted = (
        len(pass_gates) == len(REQUIRED_GATE_NAMES)
        and derived_failed == []
        and list(warnings) == []
    )

    return {
        "accepted": accepted,
        "gates": dict(normalized),
        "required_gate_count": len(REQUIRED_GATE_NAMES),
        "pass_gate_count": len(pass_gates),
        "fail_gate_count": len(failed_state_gates),
        "not_run_gate_count": len(not_run_gates),
        "not_run_gates": not_run_gates,
        "failed_state_gates": failed_state_gates,
        "failed_gates": derived_failed,
        "warnings": list(warnings),
    }


def validate_core_report_consistency(report: Mapping[str, Any]) -> dict[str, Any]:
    contradictions = []
    stored_accepted = report.get("accepted", False)
    gates = report.get("gates", {})
    failed_gates = report.get("failed_gates", [])
    warnings = report.get("warnings", [])
    dbt = report.get("dbt", {})

    # 1. accepted vs gate states
    for name in REQUIRED_GATE_NAMES:
        gs = gates.get(name, "NOT_RUN")
        if stored_accepted is True and gs != "PASS":
            contradictions.append(f"accepted=true but gate {name}={gs}")

    # 2. accepted vs failed_gates
    if stored_accepted is True and list(failed_gates):
        contradictions.append(f"accepted=true but failed_gates non-empty: {list(failed_gates)[:5]}")

    # 3. accepted vs warnings
    if stored_accepted is True and list(warnings):
        contradictions.append(f"accepted=true but warnings non-empty: {list(warnings)[:5]}")

    # 4. accepted vs dbt evidence
    if stored_accepted is True:
        if dbt.get("artifacts_separated") is not True:
            contradictions.append("accepted=true but artifacts_separated != true")
        mr = dbt.get("model_results_sha256", "")
        tr = dbt.get("test_results_sha256", "")
        if (
            isinstance(mr, str)
            and isinstance(tr, str)
            and len(mr) == 64
            and len(tr) == 64
            and mr == tr
        ):
            contradictions.append("accepted=true but model hash == test hash")

    # 5. Re-derive dbt gates from report dbt evidence
    stored_dm = gates.get("dbt_models", "NOT_RUN")
    recomputed_dm, _ = derive_dbt_model_gate(dbt) if dbt else ("NOT_RUN", [])
    if stored_dm != recomputed_dm:
        contradictions.append(f"dbt_models: stored={stored_dm} recomputed={recomputed_dm}")

    stored_dt = gates.get("dbt_tests", "NOT_RUN")
    recomputed_dt, _ = derive_dbt_test_gate(dbt) if dbt else ("NOT_RUN", [])
    if stored_dt != recomputed_dt:
        contradictions.append(f"dbt_tests: stored={stored_dt} recomputed={recomputed_dt}")

    # 6. FAIL/NOT_RUN gates must appear in failed_gates
    for name in REQUIRED_GATE_NAMES:
        gs = gates.get(name, "NOT_RUN")
        if gs in ("FAIL", "NOT_RUN") and name not in failed_gates:
            contradictions.append(f"gate {name}={gs} not in failed_gates")

    recomputed = compute_core_acceptance(
        gates=gates, failed_gates=list(failed_gates), warnings=list(warnings)
    )
    stored_matches = stored_accepted == recomputed["accepted"]

    consistency_accepted = len(contradictions) == 0
    return {
        "measurement_completed": True,
        "recomputed_accepted": recomputed["accepted"],
        "stored_accepted": stored_accepted,
        "stored_matches_recomputed": stored_matches,
        "recomputed_dbt_models_gate": recomputed_dm,
        "stored_dbt_models_gate": stored_dm,
        "recomputed_dbt_tests_gate": recomputed_dt,
        "stored_dbt_tests_gate": stored_dt,
        "contradiction_count": len(contradictions),
        "contradictions": contradictions,
        "accepted": consistency_accepted,
    }
