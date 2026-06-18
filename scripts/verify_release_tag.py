"""Verify a release tag contains correct evidence files.

Usage:
    python scripts/verify_release_tag.py \
        --tag portfolio-v1.2.11 \
        --expected-code-commit <sha> \
        --expected-evidence-commit <sha> \
        --output reports/portfolio/portfolio_v1_2_11_tag_audit.json
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent


def _git_show(tag: str, path: str) -> str:
    r = subprocess.run(
        ["git", "show", f"{tag}:{path}"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT),
        timeout=15,
    )
    if r.returncode != 0:
        return ""
    return r.stdout


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tag", required=True)
    p.add_argument("--expected-code-commit", required=True)
    p.add_argument("--expected-evidence-commit", required=True)
    p.add_argument("--output", default="reports/portfolio/portfolio_tag_audit.json")
    args = p.parse_args()

    tag = args.tag
    code_commit = args.expected_code_commit
    evidence_commit = args.expected_evidence_commit
    failures = []

    # Verify tag points to evidence commit
    r = subprocess.run(
        ["git", "rev-list", "-n", "1", tag],
        capture_output=True,
        text=True,
        cwd=str(PROJECT),
        timeout=10,
    )
    tag_target = r.stdout.strip()
    if not tag_target.startswith(evidence_commit) and not evidence_commit.startswith(tag_target):
        failures.append(f"tag {tag} points to {tag_target[:12]}, expected {evidence_commit[:12]}")

    # Verify Core report in tag
    core_json = _git_show(tag, "reports/portfolio/core_release_acceptance.json")
    if not core_json:
        failures.append("Core acceptance report not found in tag")
    else:
        try:
            core = json.loads(core_json)
            core_cc = core.get("git", {}).get("verified_code_commit", "")
            if not (core_cc.startswith(code_commit) or code_commit.startswith(core_cc)):
                failures.append(
                    f"Tag Core verified_code_commit={core_cc[:12]}, expected {code_commit[:12]}"
                )
            if not core.get("accepted"):
                failures.append("Tag Core accepted=false")
        except json.JSONDecodeError:
            failures.append("Tag Core report is not valid JSON")

    # Verify snapshot in tag
    snap_json = _git_show(tag, "reports/portfolio/data_quality_snapshot.json")
    if not snap_json:
        failures.append("Snapshot not found in tag")
    else:
        try:
            snap = json.loads(snap_json)
            snap_cc = snap.get("git", {}).get("verified_code_commit", "")
            if snap_cc[:12] != code_commit[:12]:
                failures.append(f"Tag Snapshot verified_code_commit={snap_cc[:12]}")
        except json.JSONDecodeError:
            failures.append("Tag Snapshot is not valid JSON")

    # Verify truthfulness in tag
    truth_json = _git_show(tag, "reports/portfolio/dashboard_truthfulness.json")
    if not truth_json:
        failures.append("Truthfulness report not found in tag")

    # Verify machine summary in tag
    summary_json = _git_show(tag, "reports/portfolio/p2_8_3_machine_summary.json")
    if not summary_json:
        failures.append("Machine summary not found in tag")

    accepted = len(failures) == 0 and (
        tag_target.startswith(evidence_commit) or evidence_commit.startswith(tag_target)
    )

    audit = {
        "tag": tag,
        "tag_target": tag_target,
        "expected_code_commit": code_commit,
        "expected_evidence_commit": evidence_commit,
        "core_in_tag": bool(core_json),
        "snapshot_in_tag": bool(snap_json),
        "truthfulness_in_tag": bool(truth_json),
        "summary_in_tag": bool(summary_json),
        "accepted": accepted,
        "failures": failures,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2, default=str)

    if accepted:
        print(f"Tag audit passed: {tag}")
        sys.exit(0)
    else:
        print(f"Tag audit FAILED: {tag}")
        for f_ in failures:
            print(f"  - {f_}")
        sys.exit(1)


if __name__ == "__main__":
    main()
