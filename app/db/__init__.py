import os
from contextlib import contextmanager
from typing import Iterator

import duckdb


def get_duckdb_path() -> str:
    """Resolve DuckDB file path from environment, defaulting to instance dir."""
    return os.getenv("DUCKDB_PATH", os.path.join("instance", "analytics.duckdb"))


@contextmanager
def duckdb_session(read_only: bool = True) -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield a DuckDB connection. Write mode allowed when read_only is False."""
    path = get_duckdb_path()
    database = f"{path}{'' if not read_only else '?access_mode=read_only'}"
    conn = duckdb.connect(database=database, read_only=read_only)
    try:
        yield conn
    finally:
        conn.close()
