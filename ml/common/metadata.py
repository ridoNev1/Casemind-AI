from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from collections import Counter

import duckdb


@dataclass(frozen=True)
class RunMetadata:
    """Container for generic run metadata."""

    run_id: str
    executed_at: datetime


def _connect(duckdb_path: str):
    path = duckdb_path
    if not path:
        raise FileNotFoundError("DuckDB path is not configured for metadata logging.")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    return duckdb.connect(path)


def ensure_metadata_tables(duckdb_path: str | None) -> None:
    """Ensure DuckDB metadata tables exist and contain required columns."""
    if not duckdb_path:
        return

    with _connect(duckdb_path) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS ruleset_versions (
                version TEXT PRIMARY KEY,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS etl_runs (
                run_id TEXT PRIMARY KEY,
                executed_at TIMESTAMP NOT NULL,
                ruleset_version TEXT,
                rows_processed BIGINT,
                notes TEXT
            );
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS ml_model_versions (
                run_id TEXT PRIMARY KEY,
                version TEXT,
                refreshed_at TIMESTAMP NOT NULL,
                summary_timestamp TEXT,
                rows_scored BIGINT,
                total_rows BIGINT,
                top_k INTEGER,
                top_k_amount_mean DOUBLE,
                top_k_cost_zscore_mean DOUBLE,
                top_k_los_le_1_ratio DOUBLE,
                top_k_risk_score_mean DOUBLE,
                top_k_ml_score_mean DOUBLE,
                top_k_snapshot TEXT
            );
            """
        )

        # Handle schema evolution: add missing columns if table already existed.
        con.execute(
            """
            ALTER TABLE ml_model_versions ADD COLUMN IF NOT EXISTS top_k_snapshot TEXT;
            """
        )


def record_ruleset_version(
    duckdb_path: str | None,
    version: str | None,
    description: str | None = None,
) -> None:
    """Register ruleset version once."""
    if not duckdb_path or not version:
        return

    ensure_metadata_tables(duckdb_path)
    with _connect(duckdb_path) as con:
        con.execute(
            """
            INSERT INTO ruleset_versions (version, description, created_at)
            SELECT ?, ?, CURRENT_TIMESTAMP
            WHERE NOT EXISTS (
                SELECT 1 FROM ruleset_versions WHERE version = ?
            );
            """,
            [version, description or "", version],
        )


def record_etl_run(
    duckdb_path: str | None,
    ruleset_version: str | None,
    rows_processed: int,
    notes: str | None = None,
) -> RunMetadata | None:
    """Persist ETL run metadata."""
    if not duckdb_path:
        return None

    ensure_metadata_tables(duckdb_path)
    run_id = str(uuid.uuid4())
    executed_at = datetime.now(tz=timezone.utc)

    with _connect(duckdb_path) as con:
        con.execute(
            """
            INSERT INTO etl_runs (run_id, executed_at, ruleset_version, rows_processed, notes)
            VALUES (?, ?, ?, ?, ?);
            """,
            [run_id, executed_at, ruleset_version, rows_processed, notes],
        )

    return RunMetadata(run_id=run_id, executed_at=executed_at)


def _dict_to_json(payload: Mapping[str, Any] | None) -> str | None:
    if not payload:
        return None
    return json.dumps(payload, default=_json_serializer)


def _json_serializer(value: Any) -> Any:
    """Best-effort fallback for numpy/pandas types when dumping JSON."""
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return str(value)
    if isinstance(value, (set, frozenset)):
        return list(value)
    return str(value)


def _to_python(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_to_python(v) for v in value]
    if isinstance(value, Mapping):
        return {k: _to_python(v) for k, v in value.items()}
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return str(value)
    return value


def _normalise_top_records(records: Sequence[Mapping[str, Any]] | None, limit: int = 10) -> list[dict[str, Any]]:
    if not records:
        return []
    normalised: list[dict[str, Any]] = []
    for record in records[:limit]:
        normalised.append({key: _to_python(value) for key, value in record.items()})
    return normalised


def _derive_top_k_insights(records: Sequence[Mapping[str, Any]] | None) -> dict[str, Any]:
    if not records:
        return {}

    province_counter: Counter[str] = Counter()
    severity_counter: Counter[str] = Counter()
    flag_counter: Counter[str] = Counter()

    for record in records:
        province = record.get("province_name")
        if province:
            province_counter.update([str(province)])
        severity = record.get("severity_group")
        if severity:
            severity_counter.update([str(severity)])
        for flag in record.get("flags", []) or []:
            flag_counter.update([str(flag)])

    return {
        "top_provinces": province_counter.most_common(5),
        "top_severity": severity_counter.most_common(5),
        "top_flags": flag_counter.most_common(5),
    }


def record_ml_refresh(
    duckdb_path: str | None,
    version: str,
    rows_scored: int,
    summary: Mapping[str, Any] | None,
    top_records: Sequence[Mapping[str, Any]] | None = None,
) -> RunMetadata | None:
    """Persist ML refresh metadata along with Top-K snapshot."""
    if not duckdb_path:
        return None

    ensure_metadata_tables(duckdb_path)
    run_id = str(uuid.uuid4())
    refreshed_at = datetime.now(tz=timezone.utc)
    summary_timestamp = summary.get("timestamp") if summary else None

    normalised_records = _normalise_top_records(top_records, limit=10)
    snapshot_payload = {
        "summary": _to_python(summary or {}),
        "top_records": normalised_records,
        "insights": _derive_top_k_insights(normalised_records),
    }

    with _connect(duckdb_path) as con:
        con.execute(
            """
            INSERT INTO ml_model_versions (
                run_id,
                version,
                refreshed_at,
                summary_timestamp,
                rows_scored,
                total_rows,
                top_k,
                top_k_amount_mean,
                top_k_cost_zscore_mean,
                top_k_los_le_1_ratio,
                top_k_risk_score_mean,
                top_k_ml_score_mean,
                top_k_snapshot
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            [
                run_id,
                version,
                refreshed_at,
                summary_timestamp,
                rows_scored,
                _to_python(summary.get("total_rows") if summary else None),
                _to_python(summary.get("top_k") if summary else None),
                _to_python(summary.get("amount_claimed_top_k_mean") if summary else None),
                _to_python(summary.get("cost_zscore_top_k_mean") if summary else None),
                _to_python(summary.get("los_le_1_ratio_top_k") if summary else None),
                _to_python(summary.get("risk_score_top_k_mean") if summary else None),
                _to_python(summary.get("ml_score_top_k_mean") if summary else None),
                _dict_to_json(snapshot_payload),
            ],
        )

    return RunMetadata(run_id=run_id, executed_at=refreshed_at)
