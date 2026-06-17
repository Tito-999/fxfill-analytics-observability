"""Metric definitions for dashboard display."""

METRIC_DEFINITIONS = {
    "export_rate": {
        "name": "Export Rate",
        "definition": "Tasks with form_exported / tasks with document_uploaded",
        "grain": "daily",
        "direction": "higher_is_better",
        "unit": "rate",
    },
    "dau": {
        "name": "DAU",
        "definition": "Distinct users with at least one product event per day",
        "grain": "daily",
        "direction": "higher_is_better",
        "unit": "count",
    },
    "agent_success_rate": {
        "name": "Agent Success Rate",
        "definition": "Agent runs with success_flag=true / total runs",
        "grain": "daily",
        "direction": "higher_is_better",
        "unit": "rate",
    },
    "p95_latency_ms": {
        "name": "P95 Latency",
        "definition": "95th percentile of agent run total_latency_ms",
        "grain": "daily",
        "direction": "lower_is_better",
        "unit": "ms",
    },
    "cost_per_successful_task": {
        "name": "Cost per Successful Task",
        "definition": "Total estimated cost / successfully exported tasks",
        "grain": "daily",
        "direction": "lower_is_better",
        "unit": "USD",
    },
    "d7_retention": {
        "name": "D7 Retention",
        "definition": "Users active on signup_date+7 / total eligible users",
        "grain": "cohort",
        "direction": "higher_is_better",
        "unit": "rate",
    },
    "abandonment_rate": {
        "name": "Abandonment Rate",
        "definition": "Tasks abandoned / total tasks",
        "grain": "daily",
        "direction": "lower_is_better",
        "unit": "rate",
    },
    "field_accuracy": {
        "name": "Field Accuracy",
        "definition": "Average agent field_accuracy score per run",
        "grain": "run",
        "direction": "higher_is_better",
        "unit": "score",
    },
}


def get_metric_help(metric_key: str) -> str:
    m = METRIC_DEFINITIONS.get(metric_key, {})
    return f"{m.get('name','')}: {m.get('definition','')}. Direction: {m.get('direction','')}."
