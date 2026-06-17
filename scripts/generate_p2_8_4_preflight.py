"""Generate P2.8.4 preflight JSON from real git measurements."""
import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
OUT = PROJECT / "reports" / "portfolio" / "p2_8_4_preflight.json"
SHA40 = re.compile(r'^[0-9a-f]{40}$')


def run(args, timeout=15):
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=str(PROJECT))
    return r.stdout.strip(), r.returncode


def run_lines(args):
    out, rc = run(args)
    return [x for x in out.split("\n") if x.strip()], rc


def parse_remote_sha(line):
    if not line:
        return None
    parts = line.split()
    return parts[0] if len(parts) == 2 else None


branch, _ = run(["git", "branch", "--show-current"])
status_before, _ = run(["git", "status", "--porcelain=v1"])
status_before_list = status_before.split("\n") if status_before.strip() else []

head, _ = run(["git", "rev-parse", "HEAD"])
origin_master, _ = run(["git", "rev-parse", "origin/master"])
local_tag_obj, _ = run(["git", "rev-parse", "refs/tags/portfolio-v1.2.11"])
local_tag_peeled, _ = run(["git", "rev-parse", "refs/tags/portfolio-v1.2.11^{}"])
tags_raw, _ = run(["git", "tag", "--list", "portfolio-v1.2.*"])
tags_list = [t for t in tags_raw.split("\n") if t.strip()]

remote_obj_lines, _ = run_lines(["git", "ls-remote", "--tags", "origin", "refs/tags/portfolio-v1.2.11"])
remote_obj = parse_remote_sha(remote_obj_lines[0]) if remote_obj_lines else None
remote_peeled_lines, _ = run_lines(["git", "ls-remote", "--tags", "origin", "refs/tags/portfolio-v1.2.11^{}"])
remote_peeled = parse_remote_sha(remote_peeled_lines[0]) if remote_peeled_lines else None

def _sha_ok(v):
    return True if (v and SHA40.fullmatch(str(v))) else False

sha_validation = {
    "head_full_sha": _sha_ok(head),
    "origin_master_full_sha": _sha_ok(origin_master),
    "baseline_local_tag_object_sha": _sha_ok(local_tag_obj),
    "baseline_local_peeled_commit_sha": _sha_ok(local_tag_peeled),
    "baseline_remote_tag_object_sha": _sha_ok(remote_obj),
    "baseline_remote_peeled_commit_sha": _sha_ok(remote_peeled),
}

baseline_exists_locally = _sha_ok(local_tag_obj)
baseline_exists_remotely = _sha_ok(remote_obj)

all_sha_valid = all(sha_validation.values())
measurement_completed = (
    bool(branch)
    and all_sha_valid
    and baseline_exists_locally
    and baseline_exists_remotely
)

head_matches_origin = head == origin_master
local_remote_peeled_match = local_tag_peeled == remote_peeled

machine_result = (
    measurement_completed
    and branch == "master"
    and head_matches_origin
    and len(status_before_list) == 0
    and all_sha_valid
    and baseline_exists_locally
    and baseline_exists_remotely
    and local_remote_peeled_match
)

preflight = {
    "schema_version": "1.0.0",
    "measurement_completed": measurement_completed,
    "branch": branch,
    "head_full_sha": head,
    "origin_master_full_sha": origin_master,
    "working_tree_entries_before_report": status_before_list,
    "baseline_tag": "portfolio-v1.2.11",
    "baseline_local_tag_object_full_sha": local_tag_obj,
    "baseline_local_peeled_commit_full_sha": local_tag_peeled,
    "baseline_remote_tag_object_full_sha": remote_obj,
    "baseline_remote_peeled_commit_full_sha": remote_peeled,
    "portfolio_tags": tags_list,
    "sha_validation": sha_validation,
    "head_matches_origin_master": head_matches_origin,
    "local_and_remote_peeled_targets_match": local_remote_peeled_match,
    "baseline_tag_exists_locally": baseline_exists_locally,
    "baseline_tag_exists_remotely": baseline_exists_remotely,
    "continuation_gate": {
        "expression": "branch == master AND head == origin/master AND working_tree_before is empty AND all SHA fields are 40-char AND local peeled == remote peeled",
        "raw_operands": {
            "branch": branch,
            "head_full_sha": head,
            "origin_master_full_sha": origin_master,
            "working_tree_entries_before_report": status_before_list,
            "sha_validation": sha_validation,
            "baseline_local_peeled_commit_full_sha": local_tag_peeled,
            "baseline_remote_peeled_commit_full_sha": remote_peeled,
        },
        "machine_result": machine_result,
    },
    "failures": [],
}

OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(preflight, f, indent=2)
print(f"Preflight written to {OUT}")
print(f"machine_result={machine_result}")
