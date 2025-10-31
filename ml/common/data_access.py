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
from typing import Optional

import duckdb
import pandas as pd
import yaml

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
    ) -> pd.DataFrame:
        """
        Load claims_normalized table via DuckDB.

        Args:
            limit: optional number of rows to fetch
            columns: optional subset of columns

        Returns:
            pandas.DataFrame
        """
        if not self.duckdb_path or not Path(self.duckdb_path).exists():
            raise FileNotFoundError(f"DuckDB file not found: {self.duckdb_path}")

        cols = ", ".join(columns) if columns else "*"
        limit_clause = f"LIMIT {limit}" if limit is not None else ""

        query = f"SELECT {cols} FROM {self.table_name} {limit_clause};"
        with duckdb.connect(self.duckdb_path, read_only=True) as con:
            return con.execute(query).fetchdf()

    def load_claims_parquet(self) -> pd.DataFrame:
        """Load claims_normalized parquet output (full dataset) into pandas."""
        parquet_path = self.parquet_dir / f"{self.table_name}.parquet"
        if not parquet_path.exists():
            raise FileNotFoundError(f"Parquet not found at {parquet_path}")
        return pd.read_parquet(parquet_path)

