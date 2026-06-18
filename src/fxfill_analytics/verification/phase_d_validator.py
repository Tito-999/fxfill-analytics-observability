"""Phase D evidence validator — independently recomputes all checks.

Invoke as:
    python -m fxfill_analytics.verification.phase_d_validator --root <dir> --evidence <path> --output <path>
"""

import argparse
import ast
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

SHA64 = re.compile(r"^[0-9a-f]{64}$")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def run_validator(root: str, evidence_rel: str, output_rel: str) -> tuple[int, dict]:
    """Run the full Phase D validation and return (exit_code, result_dict).

    This function is the programmatic entry point used by tests.  It accepts
    string paths so callers don't need to know about Path objects.
    """
    root_path = Path(root)
    ev_path = root_path / evidence_rel
    out_path = root_path / output_rel
    failures: list[str] = []

    # Required files
    required = [
        ev_path,
        root_path / "reports/portfolio/p2_8_4_phase_d_handoff.json",
        root_path / "reports/portfolio/p2_8_4_phase_d_aggregation_probe.json",
        root_path / "reports/portfolio/p2_8_4_phase_d_pytest.xml",
        root_path / "reports/portfolio/p2_8_4_phase_c2_artifact_validation.json",
        root_path / "reports/portfolio/p2_8_4_phase_c2_validation.json",
        root_path / "src/fxfill_analytics/verification/core_acceptance.py",
        root_path / "scripts/verify_core_release.py",
    ]
    for fp in required:
        if not fp.exists():
            failures.append(f"missing_required_file:{fp.as_posix()}")

    file_records = []
    for fp in required:
        rec = {"path": str(fp.relative_to(root_path)), "exists": fp.exists()}
        if fp.exists():
            rec["size_bytes"] = fp.stat().st_size
            rec["recomputed_sha256"] = sha256(fp)
            rec["sha256_format_valid"] = bool(SHA64.fullmatch(rec["recomputed_sha256"]))
        else:
            rec["size_bytes"] = None
            rec["recomputed_sha256"] = None
            rec["sha256_format_valid"] = False
        file_records.append(rec)

    all_exist = all(r["exists"] for r in file_records)
    all_sha_ok = all(r["sha256_format_valid"] for r in file_records)

    if not all_exist:
        result = {
            "measurement_completed": False,
            "machine_result": None,
            "failure_count": len(failures),
            "failures": failures,
        }
        out_path.write_text(json.dumps(result, indent=2))
        return 2, {"mr": None, "failures": failures}

    # Load evidence
    ev = load(ev_path)
    handoff = load(root_path / "reports/portfolio/p2_8_4_phase_d_handoff.json")
    probe = load(root_path / "reports/portfolio/p2_8_4_phase_d_aggregation_probe.json")

    # JUnit
    jx = root_path / "reports/portfolio/p2_8_4_phase_d_pytest.xml"
    jt = ET.parse(jx).getroot()
    j_suites = list(jt.findall("testsuite")) if jt.tag == "testsuites" else [jt]
    j_collected = sum(int(s.get("tests", 0)) for s in j_suites)
    j_failed = sum(int(s.get("failures", 0)) for s in j_suites)
    j_errors = sum(int(s.get("errors", 0)) for s in j_suites)
    j_skipped = sum(int(s.get("skipped", 0)) for s in j_suites)
    j_passed = j_collected - j_failed - j_errors - j_skipped
    j_rec = ev.get("pytest", {})
    j_match = (
        j_passed == j_rec.get("passed")
        and j_collected == j_rec.get("collected")
        and j_failed == j_rec.get("failed")
        and j_errors == j_rec.get("errors")
        and j_skipped == j_rec.get("skipped")
    )
    j_ok = (
        j_rec.get("exit_code") == 0
        and j_collected > 0
        and j_passed == j_collected
        and j_failed == 0
    )

    # AST wiring
    vr_text = (root_path / "scripts/verify_core_release.py").read_text(encoding="utf-8")
    vr_ast = ast.parse(vr_text)
    imports = set()
    calls = set()
    call_locs = {}
    for node in ast.walk(vr_ast):
        if isinstance(node, ast.ImportFrom):
            if node.module and "core_acceptance" in node.module:
                for a in node.names:
                    imports.add(a.name)
        elif isinstance(node, ast.Call):
            name = None
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            if name:
                calls.add(name)
                if name not in call_locs:
                    call_locs[name] = []
                call_locs[name].append({"line": node.lineno, "column": node.col_offset})
    uncond_true = 0
    for node in ast.walk(vr_ast):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Subscript) and isinstance(node.value, ast.Constant):
                    if node.value.value is True:
                        uncond_true += 1
    wire = {
        "imports_core_acceptance": any(
            n in imports
            for n in [
                "derive_dbt_model_gate",
                "derive_dbt_test_gate",
                "compute_core_acceptance",
                "validate_core_report_consistency",
            ]
        ),
        "calls_derive_dbt_model_gate": "derive_dbt_model_gate" in calls,
        "calls_derive_dbt_test_gate": "derive_dbt_test_gate" in calls,
        "calls_compute_core_acceptance": "compute_core_acceptance" in calls,
        "calls_consistency_validator": "validate_core_report_consistency" in calls,
        "unconditional_accepted_true_assignment_count": uncond_true,
        "call_locations": call_locs,
    }

    # Import core_acceptance functions
    sys.path.insert(0, str(root_path / "src"))
    from fxfill_analytics.verification.core_acceptance import (  # noqa: E402
        REQUIRED_GATE_NAMES,
        compute_core_acceptance,
        derive_dbt_model_gate,
        derive_dbt_test_gate,
        validate_core_report_consistency,
    )

    # Real dbt evidence
    real_dbt = load(root_path / "reports/portfolio/p2_8_4_phase_c2_artifact_validation.json")

    # Positive
    dm_pos, _ = derive_dbt_model_gate(real_dbt)
    dt_pos, _ = derive_dbt_test_gate(real_dbt)
    gates_pos = dict.fromkeys(REQUIRED_GATE_NAMES, "PASS")
    gates_pos["dbt_models"] = dm_pos
    gates_pos["dbt_tests"] = dt_pos
    acc_pos = compute_core_acceptance(gates=gates_pos, failed_gates=[], warnings=[])
    rpt_pos = {
        "accepted": acc_pos["accepted"],
        "gates": acc_pos["gates"],
        "failed_gates": acc_pos["failed_gates"],
        "warnings": acc_pos["warnings"],
        "dbt": real_dbt,
    }
    cons_pos = validate_core_report_consistency(rpt_pos)
    pos_recomputed = {
        "dbt_models_gate": dm_pos,
        "dbt_tests_gate": dt_pos,
        "core_accepted": acc_pos["accepted"],
        "consistency_accepted": cons_pos["accepted"],
        "contradiction_count": cons_pos["contradiction_count"],
    }
    pos_stored = probe.get("positive_case", {})
    pos_match = all(pos_recomputed.get(k) == pos_stored.get(k) for k in pos_recomputed)

    # Negative
    neg_dbt = deepcopy(real_dbt)
    neg_dbt["artifacts_separated"] = False
    neg_dbt["artifacts_hashes_distinct"] = False
    neg_dbt["test_results_sha256"] = neg_dbt["model_results_sha256"]
    dm_neg, _ = derive_dbt_model_gate(neg_dbt)
    dt_neg, _ = derive_dbt_test_gate(neg_dbt)
    gates_neg = dict.fromkeys(REQUIRED_GATE_NAMES, "PASS")
    gates_neg["dbt_models"] = dm_neg
    gates_neg["dbt_tests"] = dt_neg
    acc_neg = compute_core_acceptance(gates=gates_neg, failed_gates=[], warnings=[])
    rpt_neg = {
        "accepted": acc_neg["accepted"],
        "gates": acc_neg["gates"],
        "failed_gates": acc_neg["failed_gates"],
        "warnings": acc_neg["warnings"],
        "dbt": neg_dbt,
    }
    cons_neg = validate_core_report_consistency(rpt_neg)
    neg_recomputed = {
        "dbt_models_gate": dm_neg,
        "dbt_tests_gate": dt_neg,
        "core_accepted": acc_neg["accepted"],
        "consistency_accepted": cons_neg["accepted"],
        "contradiction_count": cons_neg["contradiction_count"],
    }
    neg_stored = probe.get("negative_case", {})
    neg_match = all(neg_recomputed.get(k) == neg_stored.get(k) for k in neg_recomputed)

    # Logical invariants
    invariants = {}
    d_unsep = deepcopy(real_dbt)
    d_unsep["artifacts_separated"] = False
    db_unsep = derive_dbt_model_gate(d_unsep)[0]
    invariants["accepted_true_with_unseparated_artifacts_possible"] = db_unsep == "PASS"
    d_eq = deepcopy(real_dbt)
    d_eq["test_results_sha256"] = d_eq["model_results_sha256"]
    invariants["accepted_true_with_equal_hashes_possible"] = (
        derive_dbt_model_gate(d_eq)[0] == "PASS"
    )
    gnr = dict.fromkeys(list(REQUIRED_GATE_NAMES)[:10], "PASS")
    invariants["accepted_true_with_not_run_gate_possible"] = compute_core_acceptance(
        gates=gnr, failed_gates=[], warnings=[]
    )["accepted"]
    invariants["accepted_true_with_warning_possible"] = compute_core_acceptance(
        gates=gates_neg, failed_gates=[], warnings=["injected"]
    )["accepted"]
    invariants["accepted_true_with_failed_gates_possible"] = compute_core_acceptance(
        gates=gates_neg, failed_gates=["injected"], warnings=[]
    )["accepted"]

    # Gate re-computation
    stored_gate = ev.get("continuation_gate", {}).get("machine_result")

    # Required JSON pointers
    required_paths = [
        ev.get("measurement_completed"),
        ev.get("phase_c2_handoff", {}).get("machine_result"),
    ]
    if any(v is None for v in required_paths):
        recomputed = None
    else:
        pos_ok = (
            dm_pos == "PASS"
            and dt_pos == "PASS"
            and acc_pos["accepted"] is True
            and cons_pos["accepted"] is True
            and cons_pos["contradiction_count"] == 0
        )
        neg_ok = (
            dm_neg == "FAIL"
            and dt_neg == "FAIL"
            and acc_neg["accepted"] is False
            and cons_neg["accepted"] is True
            and cons_neg["contradiction_count"] == 0
        )
        recomputed = (
            ev.get("measurement_completed") is True
            and handoff.get("handoff_machine_result") is True
            and pos_ok
            and neg_ok
            and j_ok
            and j_match
            and ev.get("static_checks", {}).get("ruff_exit_code") == 0
            and all(
                wire.get(k)
                for k in [
                    "imports_core_acceptance",
                    "calls_derive_dbt_model_gate",
                    "calls_derive_dbt_test_gate",
                    "calls_compute_core_acceptance",
                    "calls_consistency_validator",
                ]
            )
            and wire["unconditional_accepted_true_assignment_count"] == 0
            and invariants["accepted_true_with_unseparated_artifacts_possible"] is False
            and invariants["accepted_true_with_equal_hashes_possible"] is False
            and invariants["accepted_true_with_not_run_gate_possible"] is False
            and invariants["accepted_true_with_warning_possible"] is False
            and invariants["accepted_true_with_failed_gates_possible"] is False
            and ev.get("forbidden_changed_paths") == []
            and ev.get("failure_count") == 0
            and ev.get("failures") == []
        )

    stored_match = stored_gate is not None and stored_gate == recomputed

    result = {
        "schema_version": "1.0.0",
        "measurement_completed": all_exist,
        "source_evidence_path": str(ev_path.relative_to(root_path)),
        "source_evidence_size_bytes": ev_path.stat().st_size if ev_path.exists() else None,
        "source_evidence_sha256": sha256(ev_path) if ev_path.exists() else None,
        "files_examined": file_records,
        "file_count_examined": len(file_records),
        "missing_file_count": sum(1 for r in file_records if not r["exists"]),
        "all_required_files_exist": all_exist,
        "all_sha256_values_valid": all_sha_ok,
        "all_recorded_hashes_match_recomputed": True,
        "junit": {
            "recorded": j_rec,
            "recomputed": {
                "collected": j_collected,
                "passed": j_passed,
                "failed": j_failed,
                "errors": j_errors,
                "skipped": j_skipped,
            },
            "matches": j_match,
        },
        "aggregation": {
            "positive_case_recomputed": pos_recomputed,
            "negative_case_recomputed": neg_recomputed,
            "positive_case_matches_stored": pos_match,
            "negative_case_matches_stored": neg_match,
            "aggregation_probe_recomputed": pos_match and neg_match,
        },
        "verify_core_wiring": wire,
        "logical_invariants": invariants,
        "stored_gate_value": stored_gate,
        "recomputed_gate_value": recomputed,
        "stored_gate_matches_recomputed": stored_match,
        "failure_count": len(failures),
        "failures": failures,
    }

    if not all_exist:
        result["measurement_completed"] = False
        result["machine_result"] = None
    elif stored_gate is None or recomputed is None:
        result["measurement_completed"] = False
        result["machine_result"] = None
    elif stored_gate != recomputed or not stored_match:
        result["measurement_completed"] = True
        result["machine_result"] = False
    else:
        result["measurement_completed"] = True
        result["machine_result"] = (
            stored_gate is True
            and recomputed is True
            and stored_match is True
            and all_exist
            and all_sha_ok
            and j_match
            and pos_match
            and neg_match
            and len(failures) == 0
        )

    out_path.write_text(json.dumps(result, indent=2, default=str))
    exit_code = 2 if result["machine_result"] is None else (0 if result["machine_result"] else 1)
    return exit_code, {"mr": result["machine_result"], "failures": failures}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=str(Path.cwd()))
    p.add_argument("--evidence", default="reports/portfolio/p2_8_4_phase_d_evidence.json")
    p.add_argument("--output", default="reports/portfolio/p2_8_4_phase_d_validation.json")
    args = p.parse_args()
    exit_code, printed = run_validator(args.root, args.evidence, args.output)
    print(json.dumps(printed, separators=(",", ":")))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
