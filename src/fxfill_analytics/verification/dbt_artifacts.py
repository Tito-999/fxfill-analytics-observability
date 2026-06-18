"""Validate dbt model/test artifact separation and execution statistics.

Reads manifest + run_results from two independent dbt target directories
and produces structured evidence with re-computed counts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

STATUS_MODEL_SUCCESS = {"success", "pass"}
STATUS_MODEL_FAIL = {"fail", "failure"}
STATUS_MODEL_ERROR = {"error", "runtime_error"}
STATUS_MODEL_SKIP = {"skipped", "skip"}

STATUS_TEST_PASS = {"pass", "success"}
STATUS_TEST_FAIL = {"fail", "failure"}
STATUS_TEST_ERROR = {"error", "runtime_error"}
STATUS_TEST_SKIP = {"skipped", "skip"}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json_object(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise TypeError(f"{path} is not a JSON object")
    return data


def classify_run_results(results_path: Path) -> dict[str, Any]:
    """Classify results by unique_id prefix: model.*, test.*, other."""
    data = load_json_object(results_path)
    results = data.get("results", [])
    if not isinstance(results, list):
        return {"result_count": 0, "model_ids": 0, "test_ids": 0, "other_ids": 0, "others": []}

    model_ids = 0
    test_ids = 0
    other_ids = 0
    others = []
    for r in results:
        uid = r.get("unique_id", "")
        if uid.startswith("model."):
            model_ids += 1
        elif uid.startswith("test."):
            test_ids += 1
        else:
            other_ids += 1
            others.append(uid)

    return {
        "result_count": len(results),
        "model_ids": model_ids,
        "test_ids": test_ids,
        "other_ids": other_ids,
        "others": others,
    }


def classify_manifest_tests(manifest_path: Path) -> dict[str, int]:
    """Count models, generic tests, singular tests from manifest."""
    data = load_json_object(manifest_path)
    nodes = data.get("nodes", {})
    model_count = 0
    generic = 0
    singular = 0
    for _nid, node in nodes.items():
        rt = node.get("resource_type", "")
        if rt == "model":
            model_count += 1
        elif rt == "test":
            if node.get("test_metadata") is not None:
                generic += 1
            else:
                singular += 1
    return {
        "model_count": model_count,
        "generic_test_count": generic,
        "singular_test_count": singular,
        "test_definition_count": generic + singular,
    }


def _count_model_executions(results_path: Path, failures: list[str]) -> dict:
    data = load_json_object(results_path)
    results = data.get("results", [])
    model_success = 0
    model_fail = 0
    model_error = 0
    model_skip = 0
    model_total = 0
    distinct = set()
    for r in results:
        uid = r.get("unique_id", "")
        if not uid.startswith("model."):
            continue
        model_total += 1
        status = str(r.get("status", "")).lower()
        distinct.add(status)
        if status in STATUS_MODEL_SUCCESS:
            model_success += 1
        elif status in STATUS_MODEL_FAIL:
            model_fail += 1
        elif status in STATUS_MODEL_ERROR:
            model_error += 1
        elif status in STATUS_MODEL_SKIP:
            model_skip += 1
        else:
            failures.append(f"unknown_model_status:{status}:{uid}")
    return {
        "model_execution_count": model_total,
        "model_success_count": model_success,
        "model_fail_count": model_fail,
        "model_error_count": model_error,
        "model_skip_count": model_skip,
        "distinct_model_statuses": sorted(distinct),
    }


def _count_test_executions(results_path: Path, failures: list[str]) -> dict:
    data = load_json_object(results_path)
    results = data.get("results", [])
    test_pass = 0
    test_fail = 0
    test_error = 0
    test_skip = 0
    test_total = 0
    distinct = set()
    for r in results:
        uid = r.get("unique_id", "")
        if not uid.startswith("test."):
            continue
        test_total += 1
        status = str(r.get("status", "")).lower()
        distinct.add(status)
        if status in STATUS_TEST_PASS:
            test_pass += 1
        elif status in STATUS_TEST_FAIL:
            test_fail += 1
        elif status in STATUS_TEST_ERROR:
            test_error += 1
        elif status in STATUS_TEST_SKIP:
            test_skip += 1
        else:
            failures.append(f"unknown_test_status:{status}:{uid}")
    return {
        "test_execution_count": test_total,
        "test_pass": test_pass,
        "test_fail": test_fail,
        "test_error": test_error,
        "test_skip": test_skip,
        "distinct_test_statuses": sorted(distinct),
    }


def validate_dbt_artifacts(
    *,
    model_manifest_path: Path,
    model_results_path: Path,
    test_manifest_path: Path,
    test_results_path: Path,
) -> dict[str, Any]:
    failures: list[str] = []
    mm_exists = model_manifest_path.exists()
    mr_exists = model_results_path.exists()
    tm_exists = test_manifest_path.exists()
    tr_exists = test_results_path.exists()

    if not mm_exists:
        failures.append("model_manifest_missing")
    if not mr_exists:
        failures.append("model_results_missing")
    if not tm_exists:
        failures.append("test_manifest_missing")
    if not tr_exists:
        failures.append("test_results_missing")

    mm_sha = file_sha256(model_manifest_path) if mm_exists else ""
    mr_sha = file_sha256(model_results_path) if mr_exists else ""
    tm_sha = file_sha256(test_manifest_path) if tm_exists else ""
    tr_sha = file_sha256(test_results_path) if tr_exists else ""

    paths_distinct = (
        (model_results_path.resolve() != test_results_path.resolve())
        if (mr_exists and tr_exists)
        else False
    )
    if mr_exists and tr_exists and not paths_distinct:
        failures.append("model_results_path == test_results_path")
    hashes_distinct = (mr_sha != tr_sha) if (mr_exists and tr_exists) else False
    if mr_exists and tr_exists and not hashes_distinct:
        failures.append("model_results_sha256 == test_results_sha256")

    mr_class = (
        classify_run_results(model_results_path)
        if mr_exists
        else {"result_count": 0, "model_ids": 0, "test_ids": 0, "other_ids": 0, "others": []}
    )
    tr_class = (
        classify_run_results(test_results_path)
        if tr_exists
        else {"result_count": 0, "model_ids": 0, "test_ids": 0, "other_ids": 0, "others": []}
    )

    model_artifact_model_ids = mr_class["model_ids"]
    model_artifact_test_ids = mr_class["test_ids"]
    model_artifact_other_ids = mr_class["other_ids"]
    test_artifact_model_ids = tr_class["model_ids"]
    test_artifact_test_ids = tr_class["test_ids"]
    test_artifact_other_ids = tr_class["other_ids"]

    semantically_distinct = (
        model_artifact_model_ids > 0
        and model_artifact_test_ids == 0
        and test_artifact_test_ids > 0
        and test_artifact_model_ids == 0
    )

    if not semantically_distinct:
        failures.append("artifacts not semantically distinct")
    separated = paths_distinct and hashes_distinct and semantically_distinct

    model_exec = _count_model_executions(model_results_path, failures) if mr_exists else {}
    test_exec = _count_test_executions(test_results_path, failures) if tr_exists else {}

    model_mf = classify_manifest_tests(model_manifest_path) if mm_exists else {}
    test_mf = classify_manifest_tests(test_manifest_path) if tm_exists else {}

    mc = model_mf.get("model_count", 0)
    gtc = test_mf.get("generic_test_count", 0)
    stc = test_mf.get("singular_test_count", 0)
    tdc = gtc + stc

    accepted = (
        mm_exists
        and mr_exists
        and tm_exists
        and tr_exists
        and paths_distinct
        and hashes_distinct
        and semantically_distinct
        and separated
        and model_exec.get("model_execution_count", 0) == mc
        and model_exec.get("model_success_count", 0) == mc
        and model_exec.get("model_fail_count", 0) == 0
        and model_exec.get("model_error_count", 0) == 0
        and model_exec.get("model_skip_count", 0) == 0
        and gtc + stc == tdc
        and test_exec.get("test_execution_count", 0) == tdc
        and test_exec.get("test_pass", 0) == tdc
        and test_exec.get("test_fail", 0) == 0
        and test_exec.get("test_error", 0) == 0
        and test_exec.get("test_skip", 0) == 0
        and len(failures) == 0
    )

    return {
        "measurement_completed": True,
        "model_manifest_path": str(model_manifest_path),
        "model_results_path": str(model_results_path),
        "test_manifest_path": str(test_manifest_path),
        "test_results_path": str(test_results_path),
        "model_manifest_exists": mm_exists,
        "model_results_exists": mr_exists,
        "test_manifest_exists": tm_exists,
        "test_results_exists": tr_exists,
        "model_manifest_sha256": mm_sha,
        "model_results_sha256": mr_sha,
        "test_manifest_sha256": tm_sha,
        "test_results_sha256": tr_sha,
        "artifacts_paths_distinct": paths_distinct,
        "artifacts_hashes_distinct": hashes_distinct,
        "artifacts_semantically_distinct": semantically_distinct,
        "artifacts_separated": separated,
        "model_result_count": mr_class["result_count"],
        "model_artifact_model_ids": model_artifact_model_ids,
        "model_artifact_test_ids": model_artifact_test_ids,
        "model_artifact_other_ids": model_artifact_other_ids,
        "test_result_count": tr_class["result_count"],
        "test_artifact_model_ids": test_artifact_model_ids,
        "test_artifact_test_ids": test_artifact_test_ids,
        "test_artifact_other_ids": test_artifact_other_ids,
        "model_execution_count": model_exec.get("model_execution_count", 0),
        "model_success_count": model_exec.get("model_success_count", 0),
        "model_fail_count": model_exec.get("model_fail_count", 0),
        "model_error_count": model_exec.get("model_error_count", 0),
        "model_skip_count": model_exec.get("model_skip_count", 0),
        "distinct_model_statuses": model_exec.get("distinct_model_statuses", []),
        "test_execution_count": test_exec.get("test_execution_count", 0),
        "test_pass": test_exec.get("test_pass", 0),
        "test_fail": test_exec.get("test_fail", 0),
        "test_error": test_exec.get("test_error", 0),
        "test_skip": test_exec.get("test_skip", 0),
        "distinct_test_statuses": test_exec.get("distinct_test_statuses", []),
        "model_count": mc,
        "generic_test_count": gtc,
        "singular_test_count": stc,
        "test_definition_count": tdc,
        "accepted": accepted,
        "failures": failures,
    }
