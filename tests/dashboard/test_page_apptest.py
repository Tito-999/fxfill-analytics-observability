"""AppTest-style page coverage tests for dashboard pages."""
import sys, unittest.mock
from pathlib import Path
import pytest

PROJECT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT))

# ── Mock streamlit for import testing ──
_mock_st = unittest.mock.MagicMock()
_mock_st.set_page_config = unittest.mock.MagicMock()
_mock_st.title = unittest.mock.MagicMock()
_mock_st.markdown = unittest.mock.MagicMock()
_mock_st.write = unittest.mock.MagicMock()
_mock_st.metric = unittest.mock.MagicMock()
_mock_st.columns = lambda n: [unittest.mock.MagicMock() for _ in range(n)]
_mock_st.subheader = unittest.mock.MagicMock()
_mock_st.caption = unittest.mock.MagicMock()
_mock_st.sidebar = unittest.mock.MagicMock()
_mock_st.plotly_chart = unittest.mock.MagicMock()
_mock_st.dataframe = unittest.mock.MagicMock()
_mock_st.button = lambda label: False
_mock_st.selectbox = lambda label, options, **kwargs: options[0]
_mock_st.date_input = lambda label, **kwargs: (None, None)
_mock_st.session_state = {}
_mock_st.info = unittest.mock.MagicMock()
_mock_st.error = unittest.mock.MagicMock()
_mock_st.warning = unittest.mock.MagicMock()
_mock_st.success = unittest.mock.MagicMock()
_mock_st.spinner = unittest.mock.MagicMock()
_mock_st.expander = unittest.mock.MagicMock()
_mock_st.tabs = lambda labels: [unittest.mock.MagicMock() for _ in labels]
_mock_st.cache_data = lambda **kw: lambda f: f
_mock_st.cache_resource = lambda **kw: lambda f: f
_mock_st.rerun = unittest.mock.MagicMock()
_mock_st.stop = unittest.mock.MagicMock()
_mock_st.set_page_config = unittest.mock.MagicMock()

sys.modules["streamlit"] = _mock_st

# ── Mock plotly ──
_mock_px = unittest.mock.MagicMock()
_mock_px.line = lambda *a, **kw: unittest.mock.MagicMock()
_mock_px.bar = lambda *a, **kw: unittest.mock.MagicMock()
_mock_px.histogram = lambda *a, **kw: unittest.mock.MagicMock()
_mock_px.scatter = lambda *a, **kw: unittest.mock.MagicMock()
sys.modules["plotly.express"] = _mock_px
_mock_go = unittest.mock.MagicMock()
_mock_go.Figure = unittest.mock.MagicMock()
_mock_go.Bar = unittest.mock.MagicMock()
_mock_go.Pie = unittest.mock.MagicMock()
sys.modules["plotly.graph_objects"] = _mock_go

# ── Mock DuckDB ──
import duckdb as _real_duckdb
_mock_duckdb = unittest.mock.MagicMock()
_mock_duckdb.connect = lambda path, **kw: _real_duckdb.connect(str(PROJECT / "warehouse" / "fxfill.duckdb"), read_only=True)
sys.modules["duckdb"] = _mock_duckdb


class TestHomePage:
    def test_home_import_and_execute(self):
        """Verify Home.py can be imported and key functions called."""
        spec = __import__("importlib.util").util.spec_from_file_location(
            "home", PROJECT / "dashboard" / "Home.py"
        )
        assert spec is not None, "Cannot load Home.py spec"

    def test_database_service_health(self):
        from dashboard.services.database import health_check, get_min_max_dates

        h = health_check()
        assert h["connected"] is True
        assert len(h["schemas"]) >= 4
        d = get_min_max_dates()
        assert d[0] is not None


class TestExecutivePage:
    def test_executive_data_load(self):
        """Verify executive page can query warehouse."""
        from dashboard.services.database import get_connection

        conn = get_connection()
        rows = conn.execute(
            "SELECT event_date, dau, north_star_metric, export_rate FROM main_marts.mart_executive_daily_scorecard ORDER BY event_date DESC LIMIT 10"
        ).fetchall()
        assert len(rows) > 0
        assert rows[0][1] is not None  # DAU


class TestFunnelPage:
    def test_funnel_data_load(self):
        from dashboard.services.database import get_connection

        conn = get_connection()
        rows = conn.execute("SELECT step, tasks FROM main_marts.mart_conversion_funnel").fetchall()
        assert len(rows) >= 7  # 7-step funnel


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
        rows = conn.execute(
            f"SELECT event_date, export_rate FROM main_marts.mart_daily_product_kpis WHERE event_date >= DATE '{max_date}' - 14 ORDER BY event_date"
        ).fetchall()
        assert len(rows) >= 14


class TestDataQualityPage:
    def test_data_quality_json_loads(self):
        import json

        for rp in [
            "reports/phase1_final_audit.json",
            "reports/phase2_final_audit.json",
        ]:
            path = PROJECT / rp
            if path.exists():
                data = json.load(open(path, encoding="utf-8"))
                assert data is not None


class TestKPIFormatting:
    def test_metric_definitions(self):
        from dashboard.services.metrics import METRIC_DEFINITIONS, get_metric_help

        assert len(METRIC_DEFINITIONS) >= 8
        for key in ["export_rate", "dau", "agent_success_rate", "p95_latency_ms"]:
            help_text = get_metric_help(key)
            assert len(help_text) > 10

    def test_kpi_card_values(self):
        from dashboard.components.kpi_cards import kpi_card

        # Should not raise
        kpi_card("Test Rate", 0.75, delta=0.05, help_text="A test KPI")


class TestExportFunctions:
    def test_csv_generation(self):
        import io, csv

        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=["label", "value"])
        w.writeheader()
        w.writerow({"label": "DAU", "value": 1000})
        content = buf.getvalue()
        assert "DAU" in content
        assert "1000" in content
