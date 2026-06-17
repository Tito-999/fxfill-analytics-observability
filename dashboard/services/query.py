"""Shared parameterized query helper for dashboard pages."""
from collections.abc import Sequence

import pandas as pd

from dashboard.services.database import get_connection


def query_df(sql: str, params: Sequence[object] | None = None) -> pd.DataFrame:
    """Execute a parameterized DuckDB query and return a DataFrame."""
    connection = get_connection()
    return connection.execute(sql, list(params or [])).fetchdf()
