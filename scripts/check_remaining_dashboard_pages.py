"""Acceptance check for Feature Adoption, Agent Observability, and A/B Test pages."""
import argparse, json, os, sys
from datetime import date
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "src"))


def check_sql_contracts(db_path: str) -> dict:
    import duckdb
    conn = duckdb.connect(db_path, read_only=True)
    results = {}

    # ── Feature Adoption segmented ──
    try:
        rows = conn.execute("SELECT MIN(event_date), MAX(event_date) FROM main_marts.mart_feature_adoption_segmented").fetchone()
        d1, d2 = rows[0], rows[1]
        if d1 and d2:
            rows2 = conn.execute(
                """SELECT feature_name, user_segment, device_type, complexity,
                   SUM(total_users) AS total_users, SUM(adopted_users) AS adopted_users,
                   SUM(adopted_users)*1.0/NULLIF(SUM(total_users),0) AS adoption_rate
                   FROM main_marts.mart_feature_adoption_segmented
                   WHERE event_date BETWEEN ? AND ?
                   GROUP BY feature_name, user_segment, device_type, complexity""",
                [d1, d2],
            ).fetchall()
            ok = len(rows2) > 0
            violations = []
            for r in rows2:
                total = int(r[4]) if r[4] else 0  # idx 4 = total_users
                adopted = int(r[5]) if r[5] else 0  # idx 5 = adopted_users
                rate = float(r[6]) if r[6] else 0.0  # idx 6 = adoption_rate
                if adopted < 0 or adopted > total: violations.append(f"adopted({adopted})>total({total})")
                if rate < 0 or rate > 1: violations.append(f"rate={rate}")
            results["feature_adoption"] = {"passed": ok and len(violations)==0, "row_count": len(rows2), "failures": violations}
        else:
            results["feature_adoption"] = {"passed": False, "row_count": 0, "failures": ["empty"]}
    except Exception as e:
        results["feature_adoption"] = {"passed": False, "row_count": 0, "failures": [str(e)[:200]]}

    # ── Feature TTFU ──
    try:
        d1, d2 = conn.execute("SELECT MIN(first_use_date), MAX(first_use_date) FROM main_marts.mart_feature_time_to_first_use").fetchone()
        if d1 and d2:
            rows2 = conn.execute(
                "SELECT feature_name, days_to_first_use, SUM(user_count) FROM main_marts.mart_feature_time_to_first_use WHERE first_use_date BETWEEN ? AND ? GROUP BY feature_name, days_to_first_use",
                [d1, d2],
            ).fetchall()
            ok = len(rows2) > 0 and all(r[1] >= 0 and r[2] > 0 for r in rows2)
            results["feature_ttfu"] = {"passed": ok, "row_count": len(rows2), "failures": []}
        else:
            results["feature_ttfu"] = {"passed": False, "row_count": 0, "failures": ["empty"]}
    except Exception as e:
        results["feature_ttfu"] = {"passed": False, "row_count": 0, "failures": [str(e)[:200]]}

    # ── Agent error Pareto ──
    try:
        rows2 = conn.execute("""
            WITH grouped AS (SELECT error_category, SUM(error_count) AS error_count, SUM(affected_tasks) AS affected_tasks, AVG(avg_failed_latency_ms) AS avg_failed_latency_ms FROM main_marts.mart_error_root_cause GROUP BY error_category),
            ranked AS (SELECT error_category, error_count, error_count*1.0/NULLIF(SUM(error_count) OVER(),0) AS pct_of_total, affected_tasks, avg_failed_latency_ms FROM grouped)
            SELECT error_category, error_count, pct_of_total, SUM(pct_of_total) OVER (ORDER BY error_count DESC, error_category ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_pct, affected_tasks, avg_failed_latency_ms FROM ranked ORDER BY error_count DESC, error_category
        """).fetchall()
        ok = len(rows2) > 0
        if ok:
            last_cum = rows2[-1][3]
            if abs(last_cum - 1.0) > 1e-9:
                ok = False
        results["agent_observability"] = {"passed": ok, "row_count": len(rows2), "failures": []}
    except Exception as e:
        results["agent_observability"] = {"passed": False, "row_count": 0, "failures": [str(e)[:200]]}

    # ── A/B user metrics ──
    try:
        rows2 = conn.execute("SELECT user_id, experiment_group, total_tasks, successful_tasks, task_success_rate, avg_field_accuracy, avg_agent_latency_ms, total_cost_usd FROM main_marts.mart_ab_test_user_metrics ORDER BY experiment_group, user_id").fetchall()
        ok = len(rows2) > 0
        violations = []
        for r in rows2:
            if r[2] and r[3] and r[3] > r[2]: violations.append(f"exported>{r[2]}")
            if r[4] and (r[4] < 0 or r[4] > 1): violations.append(f"rate={r[4]}")
            if r[6] and r[6] < 0: violations.append(f"latency={r[6]}")
            if r[7] and r[7] < 0: violations.append(f"cost={r[7]}")
        results["ab_test"] = {"passed": ok and len(violations)==0, "row_count": len(rows2), "failures": violations}
    except Exception as e:
        results["ab_test"] = {"passed": False, "row_count": 0, "failures": [str(e)[:200]]}

    conn.close()
    return results


def check_page_rendering(db_path: str) -> dict:
    """Run three pages via Streamlit AppTest."""
    os.environ["FXFILL_DUCKDB_PATH"] = db_path
    os.environ["PYTHONNOUSERSITE"] = "1"
    os.environ["NO_PROXY"] = "127.0.0.1,localhost"
    os.environ["no_proxy"] = "127.0.0.1,localhost"
    os.environ["PYTHONPATH"] = str(PROJECT)

    from streamlit.testing.v1 import AppTest
    pages = {
        "3_Feature_Adoption.py": "dashboard/pages/3_Feature_Adoption.py",
        "4_Agent_Observability.py": "dashboard/pages/4_Agent_Observability.py",
        "5_AB_Test.py": "dashboard/pages/5_AB_Test.py",
    }
    results = {"checked": 0, "passed": 0, "failures": [], "catalog_exception_count": 0, "binder_exception_count": 0, "streamlit_exception_count": 0}

    for name, path in pages.items():
        try:
            app = AppTest.from_file(str(PROJECT / path))
            app.run(timeout=60)
            exc_types = [type(e.value).__name__ for e in app.exception]
            for et in exc_types:
                if "Catalog" in et: results["catalog_exception_count"] += 1
                if "Binder" in et: results["binder_exception_count"] += 1
                if "Streamlit" in et: results["streamlit_exception_count"] += 1
            if len(app.exception) == 0:
                results["passed"] += 1
            else:
                results["failures"].append({"page": name, "errors": exc_types[:3] if exc_types else [str(e.value)[:100] for e in app.exception[:3]]})
        except Exception as e:
            results["failures"].append({"page": name, "errors": [str(e)[:200]]})
        results["checked"] += 1
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--database", required=True)
    p.add_argument("--output", default="reports/portfolio/remaining_dashboard_pages.json")
    args = p.parse_args()
    db = args.database
    out = Path(args.output)
    if not Path(db).exists():
        print(f"ERROR: Database not found: {db}", file=sys.stderr)
        sys.exit(1)

    # Database contracts
    sql_results = check_sql_contracts(db)
    all_sql_ok = all(v["passed"] for v in sql_results.values())

    # Page rendering
    page_results = check_page_rendering(db)

    report = {
        "database_exists": True,
        "database_contract_passed": all_sql_ok,
        "sql_contracts": sql_results,
        "pages_checked": page_results["checked"],
        "pages_passed": page_results["passed"],
        "page_failures": page_results["failures"],
        "catalog_exception_count": page_results["catalog_exception_count"],
        "binder_exception_count": page_results["binder_exception_count"],
        "streamlit_exception_count": page_results["streamlit_exception_count"],
        "accepted": all_sql_ok and page_results["passed"] == 3,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    if report["accepted"]:
        print(f"ACCEPTED: {page_results['passed']}/3 pages, {sum(1 for v in sql_results.values() if v['passed'])}/4 SQL contracts")
        sys.exit(0)
    else:
        print(f"FAILED: pages={page_results['passed']}/{page_results['checked']}, SQL={sum(1 for v in sql_results.values() if v['passed'])}/{len(sql_results)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
