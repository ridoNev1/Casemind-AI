"""
Utility helpers for accessing analytics datasets (claims_normalized, etc).

Usage:
    from ml.common.data_access import DataLoader
    loader = DataLoader()
    df = loader.load_claims_normalized(limit=5)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Sequence

import duckdb
import pandas as pd
import yaml

from .schema import validate_claims_normalized
PIPELINE_CONFIG_PATH = Path("pipelines/claims_normalized/config.yaml")


class DataLoader:
    """Simple accessor for analytics DuckDB/parquet outputs."""

    def __init__(
        self,
        duckdb_path: Optional[str] = None,
        config_path: Path = PIPELINE_CONFIG_PATH,
    ) -> None:
        self._config = self._load_config(config_path)
        self.duckdb_path = duckdb_path or self._config.get("duckdb_path")
        output_cfg = self._config.get("output", {})
        self.parquet_dir = Path(output_cfg.get("parquet_dir", "instance/data"))
        self.table_name = output_cfg.get("table_name", "claims_normalized")

    @staticmethod
    def _load_config(path: Path) -> dict:
        if not path.exists():
            raise FileNotFoundError(f"Config not found at {path}")
        with path.open() as f:
            return yaml.safe_load(f)

    def load_claims_normalized(
        self,
        limit: Optional[int] = None,
        columns: Optional[list[str]] = None,
        filters: Optional[dict[str, object]] = None,
        validate: bool = False,
        required_columns: Optional[list[str]] = None,
    ) -> pd.DataFrame:
        """
        Load claims_normalized table via DuckDB.

        Args:
            limit: optional number of rows to fetch
            columns: optional subset of columns
            filters: optional dict mapping column -> exact-match value

        Returns:
            pandas.DataFrame
        """
        if not self.duckdb_path or not Path(self.duckdb_path).exists():
            raise FileNotFoundError(f"DuckDB file not found: {self.duckdb_path}")

        cols = ", ".join(columns) if columns else "*"
        where_clause = ""
        params: list[object] = []
        if filters:
            conditions = []
            for column, value in filters.items():
                if value is None:
                    continue
                if not self._is_safe_column_name(column):
                    raise ValueError(f"Invalid column name in filters: {column}")
                conditions.append(f"{column} = ?")
                params.append(value)
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

        limit_clause = f"LIMIT {limit}" if limit is not None else ""

        query = f"SELECT {cols} FROM {self.table_name} {where_clause} {limit_clause};"
        query = " ".join(query.split())
        with duckdb.connect(self.duckdb_path, read_only=True) as con:
            df = con.execute(query, params).fetchdf()

        if validate:
            validate_claims_normalized(df, required_columns)
        return df

    def load_claims_parquet(self) -> pd.DataFrame:
        """Load claims_normalized parquet output (full dataset) into pandas."""
        parquet_path = self.parquet_dir / f"{self.table_name}.parquet"
        if not parquet_path.exists():
            raise FileNotFoundError(f"Parquet not found at {parquet_path}")
        return pd.read_parquet(parquet_path)

    @staticmethod
    def _is_safe_column_name(column: str) -> bool:
        """Basic safeguard preventing SQL injection via column names."""
        return column.replace("_", "").isalnum()

    def write_dataframe_to_duckdb(self, df: pd.DataFrame, table_name: str, mode: str = "replace") -> None:
        """
        Persist dataframe to DuckDB table.

        Args:
            df: DataFrame to persist.
            table_name: Target table name.
            mode: Either 'replace' (default) or 'append'.
        """
        if mode not in {"replace", "append"}:
            raise ValueError("mode must be 'replace' or 'append'")

        if not self.duckdb_path:
            raise FileNotFoundError("DuckDB path not configured.")

        table = table_name
        with duckdb.connect(self.duckdb_path) as con:
            if mode == "replace":
                con.execute(f"DROP TABLE IF EXISTS {table}")
            con.register("df_view", df)
            con.execute(f"CREATE TABLE IF NOT EXISTS {table} AS SELECT * FROM df_view LIMIT 0")
            con.execute(f"INSERT INTO {table} SELECT * FROM df_view")
            con.unregister("df_view")

    def read_table_from_duckdb(self, table_name: str) -> pd.DataFrame | None:
        """Return table as DataFrame if exists, otherwise None."""
        if not self.duckdb_path:
            return None

        query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main' AND table_name = ?
        """
        with duckdb.connect(self.duckdb_path, read_only=True) as con:
            exists = con.execute(query, [table_name]).fetchone()
            if not exists:
                return None
            return con.execute(f"SELECT * FROM {table_name}").fetchdf()

    def query(self, sql: str, params: Optional[Sequence[object]] = None) -> pd.DataFrame:
        """Execute an arbitrary SQL query against DuckDB and return the results."""
        if not self.duckdb_path or not Path(self.duckdb_path).exists():
            raise FileNotFoundError(f"DuckDB file not found: {self.duckdb_path}")

        with duckdb.connect(self.duckdb_path, read_only=True) as con:
            return con.execute(sql, params or []).fetchdf()
