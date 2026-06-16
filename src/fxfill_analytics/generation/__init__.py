"""
Synthetic data generation — users, sessions, documents, product events,
agent traces, and experiment assignments.

All generators accept a seeded NumPy Generator for reproducibility.
"""

from fxfill_analytics.generation.generate_agent_traces import (
    generate_agent_runs,
    generate_agent_spans,
)
from fxfill_analytics.generation.generate_documents import generate_documents
from fxfill_analytics.generation.generate_experiment_data import (
    generate_experiment_assignments,
)
from fxfill_analytics.generation.generate_product_events import (
    generate_product_events,
)
from fxfill_analytics.generation.generate_sessions import generate_sessions
from fxfill_analytics.generation.generate_users import generate_users

__all__ = [
    "generate_users",
    "generate_documents",
    "generate_sessions",
    "generate_product_events",
    "generate_agent_runs",
    "generate_agent_spans",
    "generate_experiment_assignments",
]
