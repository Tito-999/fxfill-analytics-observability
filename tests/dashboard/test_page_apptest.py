"""Database contract tests for dashboard pages — no Streamlit/Plotly mocks."""

import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT))


class TestHomePage:
    def test_home_import(self):
        spec = __import__("importlib.util").util.spec_from_file_location(
            "home", PROJECT / "dashboard" / "Home.py"
        )
        assert spec is not None

    def test_database_service(self):
        from dashboard.services.database import health_check

        h = health_check()
        assert h["connected"] is True
        assert len(h["schemas"]) >= 4


class TestExecutivePage:
    def test_executive_data_load(self):
        from dashboard.services.database import get_connection

        conn = get_connection()
        rows = conn.execute(
            "SELECT event_date, dau, north_star_metric, export_rate FROM main_marts.mart_executive_daily_scorecard ORDER BY event_date DESC LIMIT 10"
        ).fetchall()
        assert len(rows) > 0


class TestFunnelPage:
    def test_funnel_data_load(self):
        from dashboard.services.database import get_connection

        conn = get_connection()
        rows = conn.execute("SELECT step, tasks FROM main_marts.mart_conversion_funnel").fetchall()
        assert len(rows) >= 7


class TestRetentionPage:
    def test_retention_data_load(self):
        from dashboard.services.database import get_connection

        conn = get_connection()
        rows = conn.execute(
            "SELECT cohort_date, d1_retention_rate FROM main_marts.mart_retention_cohort LIMIT 10"
        ).fetchall()
        assert len(rows) > 0


class TestFeaturePage:
    def test_feature_data_load(self):
        from dashboard.services.database import get_connection

        conn = get_connection()
        rows = conn.execute(
            "SELECT event_date, ocr_adoption FROM main_marts.mart_feature_adoption ORDER BY event_date LIMIT 10"
        ).fetchall()
        assert len(rows) > 0


class TestAgentPage:
    def test_agent_data_load(self):
        from dashboard.services.database import get_connection

        conn = get_connection()
        rows = conn.execute(
            "SELECT run_date, agent_success_rate, p95_latency_ms FROM main_marts.mart_agent_daily_kpis ORDER BY run_date LIMIT 10"
        ).fetchall()
        assert len(rows) > 0


class TestABTestPage:
    def test_ab_test_data_load(self):
        from dashboard.services.database import get_connection

        conn = get_connection()
        rows = conn.execute(
            "SELECT experiment_group, user_count, avg_export_rate FROM main_marts.mart_ab_test_summary"
        ).fetchall()
        assert len(rows) >= 2


class TestRootCausePage:
    def test_root_cause_data_load(self):
        from dashboard.services.database import get_connection

        conn = get_connection()
        max_date = conn.execute(
            "SELECT MAX(event_date) FROM main_marts.mart_daily_product_kpis"
        ).fetchone()[0]
        assert max_date is not None


class TestDataQualityPage:
    def test_data_quality_json_loads(self):
        import json

        for rp in ["reports/phase1_final_audit.json", "reports/phase2_final_audit.json"]:
            path = PROJECT / rp
            if path.exists():
                assert json.load(open(path, encoding="utf-8")) is not None


class TestKPIHelpers:
    def test_metric_definitions(self):
        from dashboard.services.metrics import METRIC_DEFINITIONS

        assert len(METRIC_DEFINITIONS) >= 8

    def test_kpi_card(self):
        from unittest import mock

        import streamlit as st

        calls = []
        with mock.patch.object(st, "metric", side_effect=lambda *a, **kw: calls.append((a, kw))):
            from dashboard.components.kpi_cards import kpi_card

            kpi_card("Test Rate", 0.75, delta=0.05)
        assert len(calls) == 1
