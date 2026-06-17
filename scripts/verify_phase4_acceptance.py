"""Machine-verifiable Phase 4 acceptance checker."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parent.parent


def _fail(msg: str, results: dict) -> None:
    results["failed_gates"].append(msg)
    results["accepted"] = False


def verify(report_dir: Path, config_path: Path) -> dict[str, Any]:
    results: dict = {
        "accepted": True,
        "failed_gates": [],
        "passed_gates": [],
        "warnings": [],
        "verified_files": [],
        "verified_figures": [],
    }

    # Verify config can be loaded
    with open(config_path) as f:
        _cfg = (
            yaml.safe_load(f)
            if (config_path.suffix == ".yaml" or config_path.suffix == ".yml")
            else json.load(f)
        )
    assert _cfg is not None, f"Failed to load config from {config_path}"

    # 1. Required files
    required_jsons = [
        "experiment_analysis.json",
        "experiment_manifest.json",
        "data_validation.json",
        "randomization_balance.json",
        "power_analysis.json",
        "performance.json",
        "phase4_final_audit.json",
    ]
    required_mds = [r.replace(".json", ".md") for r in required_jsons] + ["experiment_analysis.md"]
    required_figs = [
        "figures/assignment_balance.png",
        "figures/primary_effect.png",
        "figures/secondary_effects_forest.png",
        "figures/guardrail_forest.png",
        "figures/bootstrap_distribution.png",
        "figures/segment_effects_forest.png",
        "figures/power_curve.png",
    ]

    for fname in required_jsons + required_mds:
        p = report_dir / fname
        if p.exists() and p.stat().st_size > 0:
            results["verified_files"].append(fname)
        else:
            _fail(f"Missing/empty: {fname}", results)

    for fname in required_figs:
        p = report_dir / fname
        if not p.exists() or p.stat().st_size == 0:
            _fail(f"Missing/empty figure: {fname}", results)
            continue
        with open(p, "rb") as f:
            header = f.read(8)
            if header[:4] != b"\x89PNG":
                _fail(f"Not valid PNG: {fname}", results)
        results["verified_figures"].append(fname)

    # 2. Load experiment analysis and verify fields
    ea_path = report_dir / "experiment_analysis.json"
    if ea_path.exists():
        with open(ea_path) as f:
            ea = json.load(f)

        # Population
        pop_keys = [
            "experiment_id",
            "clean_ITT_A_n",
            "clean_ITT_B_n",
            "contaminated_users",
            "triggered_A_n",
            "triggered_B_n",
            "raw_assignment_rows",
            "unique_assigned_users",
        ]
        for k in pop_keys:
            if k not in ea or ea[k] is None:
                _fail(f"Missing population field: {k}", results)
        if ea.get("clean_ITT_A_n", 0) + ea.get("clean_ITT_B_n", 0) != ea.get("clean_ITT_users", 0):
            _fail("clean_ITT_A_n + clean_ITT_B_n != clean_ITT_users", results)

        # SRM
        srm_fields = ["A_count", "B_count", "chi_square", "p_value", "srm_alpha", "srm_detected"]
        for srm_name in ["raw_assignment_SRM", "clean_ITT_SRM"]:
            srm = ea.get(srm_name, {})
            for k in srm_fields:
                if k not in srm or srm[k] is None:
                    _fail(f"Missing SRM field: {srm_name}.{k}", results)

        # Balance
        bal = ea.get("randomization_balance", {})
        if bal.get("max_absolute_SMD") is None:
            _fail("Missing max_absolute_SMD", results)

        # Primary
        prim = ea.get("primary", {})
        prim_keys = [
            "metric_name",
            "estimand",
            "A_n",
            "B_n",
            "A_value",
            "B_value",
            "absolute_effect",
            "relative_uplift",
            "risk_ratio",
            "absolute_effect_CI_lower",
            "absolute_effect_CI_upper",
            "raw_p_value",
            "practical_threshold",
        ]
        for k in prim_keys:
            if k not in prim or prim[k] is None:
                _fail(f"Missing primary field: {k}", results)

        # Bootstrap
        boot = ea.get("bootstrap", {})
        if boot.get("iterations", 0) < 5000:
            _fail(f"Bootstrap iterations {boot.get('iterations')} < 5000", results)

        # Secondary
        sec = ea.get("secondary_metrics", [])
        if len(sec) < 3:
            _fail(f"Secondary metrics: expected >=3, got {len(sec)}", results)

        # Guardrails
        grd = ea.get("guardrails", [])
        if len(grd) < 4:
            _fail(f"Guardrails: expected >=4, got {len(grd)}", results)

        # Decision
        dec = ea.get("decision", {})
        valid_decisions = [
            "SHIP",
            "SHIP_WITH_MONITORING",
            "CONTINUE_EXPERIMENT",
            "STOP_FOR_HARM",
            "INCONCLUSIVE",
        ]
        if dec.get("recommendation") not in valid_decisions:
            _fail(f"Invalid/explicit decision: {dec.get('recommendation')}", results)

        # Forbidden placeholders
        text_check = json.dumps(ea)
        for forbidden in ["TBD", "deferred", "in report module", "rule-based"]:
            if forbidden in text_check:
                _fail(f"Forbidden placeholder found: '{forbidden}'", results)

        results["population_checks"] = {k: ea.get(k) for k in pop_keys}
        results["primary_summary"] = {
            k: prim.get(k) for k in ["metric_name", "A_value", "B_value", "absolute_effect"]
        }
        results["decision"] = dec.get("recommendation")

    # 3. Performance
    perf_path = report_dir / "performance.json"
    if perf_path.exists():
        with open(perf_path) as f:
            perf = json.load(f)
        total = perf.get("full_analysis_seconds", 999)
        if total >= 120:
            _fail(f"Analysis time {total}s >= 120s", results)
        results["performance_seconds"] = total

    # 4. Simulation
    sim_path = report_dir / "experiment_analysis.json"
    if sim_path.exists():
        with open(sim_path) as f:
            sim_data = json.load(f)
        aa = sim_data.get("aa_simulation", {})
        if aa.get("simulation_count", 0) < 1000:
            _fail(f"A/A sims: {aa.get('simulation_count')} < 1000", results)
        fpr = aa.get("false_positive_rate", 1.0)
        if not (0.03 <= fpr <= 0.07):
            _fail(f"A/A FPR {fpr} outside [0.03,0.07]", results)
        ab = sim_data.get("ab_recovery", {})
        if ab.get("simulation_count", 0) < 500:
            _fail(f"A/B sims: {ab.get('simulation_count')} < 500", results)
        results["aa_fpr"] = fpr
        results["ab_power"] = ab.get("empirical_power", 0)

    # 5. Summary
    results["verified_file_count"] = len(results["verified_files"])
    results["verified_figure_count"] = len(results["verified_figures"])
    results["passed"] = results["accepted"] and len(results["failed_gates"]) == 0

    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--report-dir", required=True)
    p.add_argument("--config", required=True)
    args = p.parse_args()
    rd = Path(args.report_dir)
    cf = Path(args.config)

    results = verify(rd, cf)
    out_dir = rd
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "phase4_acceptance.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    md = [
        "# Phase 4 Acceptance\n",
        f"Accepted: **{results['accepted']}**\n",
        f"Passed gates: {len(results['passed_gates'])}, Failed: {len(results['failed_gates'])}\n",
        f"Verified files: {len(results['verified_files'])}, Figures: {results['verified_figure_count']}\n",
        f"A/A FPR: {results.get('aa_fpr','?')}, A/B Power: {results.get('ab_power','?')}\n",
        f"Performance: {results.get('performance_seconds','?')}s\n",
    ]
    if results["failed_gates"]:
        md.append("\n## FAILED\n")
        for g in results["failed_gates"]:
            md.append(f"- {g}\n")
    with open(out_dir / "phase4_acceptance.md", "w") as f:
        f.write("".join(md))

    if not results["accepted"]:
        print(f"ACCEPTANCE FAILED: {len(results['failed_gates'])} gates failed")
        sys.exit(1)
    print("ACCEPTANCE PASSED")
    sys.exit(0)


if __name__ == "__main__":
    import yaml

    main()
