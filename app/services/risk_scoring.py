from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any
import os

import json
import numpy as np
import pandas as pd
from flask import current_app

from ml.common.data_access import DataLoader
from ml.inference.scorer import MLScorer
from ..models import AuditOutcome

DEFAULT_PAGE_SIZE = 50
SCORES_CACHE_FILENAME = "claims_ml_scores.parquet"
SCORES_CACHE_TABLE = "claims_ml_scores"
QC_LOG_DIRNAME = "instance/logs"
QC_TOP_K = 50
MAX_FETCH_ROWS = int(os.getenv("CLAIMS_MAX_QUERY_ROWS", "200000"))


def get_high_risk_claims(filters: Mapping[str, Any]) -> dict[str, Any]:
    loader = DataLoader()
    scorer = MLScorer()

    df, total_count = _fetch_filtered_claims(loader, filters)
    if df.empty:
        return _build_response([], total=0, page=1, page_size=_determine_page_size(filters), ruleset_version=_get_ruleset_version(), model_version=scorer.model_version)

    scores_cache = _load_or_compute_scores(loader, scorer, force_refresh=_should_refresh_cache(filters))
    scores_subset = scores_cache[scores_cache["claim_id"].isin(df["claim_id"])]
    if scores_subset.empty:
        # fallback: score subset if cache missing entries
        scores_subset = scorer.score_dataframe(df)
    df = df.merge(scores_subset, on="claim_id", how="left")
    df = _compute_rule_enrichment(df)

    df["risk_score"] = df[["rule_score", "ml_score_normalized"]].max(axis=1).fillna(0)
    df = _apply_advanced_filters(df, filters)
    df["flag_count"] = df["flags"].apply(lambda value: len(value) if isinstance(value, list) else 0)
    df["has_flags"] = df["flag_count"] > 0
    df = df.sort_values(
        by=["has_flags", "flag_count", "risk_score"],
        ascending=[False, False, False],
    )

    page_size = _determine_page_size(filters)
    page = _determine_page(filters)
    start = (page - 1) * page_size
    end = start + page_size
    paged_df = df.iloc[start:end].copy()
    paged_df = paged_df.drop(columns=["flag_count", "has_flags"], errors="ignore")

    ruleset_version = _get_ruleset_version()

    results: list[dict[str, Any]] = []
    latest_feedback_map = _fetch_latest_feedback_map(paged_df["claim_id"].tolist())

    for row in paged_df.itertuples(index=False):
        results.append(
            {
                "claim_id": row.claim_id,
                "province_name": row.province_name,
                "dx_primary_code": row.dx_primary_code,
                "dx_primary_label": getattr(row, "dx_primary_label", None),
                "dx_primary_group": getattr(row, "dx_primary_group", None),
                "dx_secondary_codes": _to_optional_list(getattr(row, "dx_secondary_codes", None)),
                "dx_secondary_labels": _to_optional_list(getattr(row, "dx_secondary_labels", None)),
                "facility_id": _to_optional_str(getattr(row, "facility_id", None)),
                "facility_name": _to_optional_title(getattr(row, "facility_name", None)),
                "facility_match_quality": _to_optional_str(getattr(row, "facility_match_quality", None)),
                "facility_names_region": getattr(row, "region_facility_names", None),
                "facility_ownership_names_region": getattr(row, "region_ownership_names", None),
                "facility_type_names_region": getattr(row, "region_facility_type_names", None),
                "facility_class_names_region": getattr(row, "region_facility_class_names", None),
                "severity_group": row.severity_group,
                "service_type": getattr(row, "service_type", None),
                "facility_class": getattr(row, "facility_class", None),
                "amount_claimed": _to_optional_float(row.amount_claimed),
                "amount_paid": _to_optional_float(row.amount_paid),
                "cost_zscore": _to_optional_float(row.cost_zscore),
                "los": _to_optional_int(row.los),
                "bpjs_payment_ratio": _to_optional_float(row.bpjs_payment_ratio),
                "admit_dt": _to_optional_date(getattr(row, "admit_dt", None)),
                "discharge_dt": _to_optional_date(getattr(row, "discharge_dt", None)),
                "peer": {
                    "mean": _to_optional_float(row.peer_mean),
                    "p90": _to_optional_float(row.peer_p90),
                },
                "flags": row.flags,
                "duplicate_pattern": bool(getattr(row, "duplicate_pattern", False)),
                "rule_score": _to_optional_float(row.rule_score),
                "ml_score": _to_optional_float(row.ml_score),
                "ml_score_normalized": _to_optional_float(row.ml_score_normalized),
                "risk_score": _to_optional_float(row.risk_score),
                "model_version": row.model_version,
                "ruleset_version": ruleset_version,
                "latest_feedback": latest_feedback_map.get(row.claim_id),
            }
        )

    return _build_response(
        results,
        total=total_count,
        page=page,
        page_size=page_size,
        ruleset_version=ruleset_version,
        model_version=scorer.model_version,
    )


def _fetch_filtered_claims(loader: DataLoader, filters: Mapping[str, Any]) -> tuple[pd.DataFrame, int]:
    clauses: list[str] = []
    params: list[Any] = []

    def add_equals(column: str, value: Any, transform=None) -> None:
        if value is None or value == "":
            return
        val = transform(value) if transform else value
        clauses.append(f"{column} = ?")
        params.append(val)

    add_equals("province_name", filters.get("province"), lambda v: str(v).upper())
    add_equals("dx_primary_code", filters.get("dx"), lambda v: str(v).upper())
    add_equals("facility_class", filters.get("facility_class"))
    add_equals("LOWER(severity_group)", filters.get("severity"), lambda v: str(v).lower())
    add_equals("UPPER(service_type)", filters.get("service_type"), lambda v: str(v).upper())

    start_date = filters.get("start_date")
    end_date = filters.get("end_date")
    discharge_start = filters.get("discharge_start")
    discharge_end = filters.get("discharge_end")

    if start_date:
        clauses.append("admit_dt >= ?")
        params.append(start_date)
    if end_date:
        clauses.append("admit_dt <= ?")
        params.append(end_date)
    if discharge_start:
        clauses.append("discharge_dt >= ?")
        params.append(discharge_start)
    if discharge_end:
        clauses.append("discharge_dt <= ?")
        params.append(discharge_end)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    count_sql = f"SELECT COUNT(*) AS total FROM {loader.table_name} {where_sql}"
    total_df = loader.query(count_sql, params)
    total = int(total_df["total"].iloc[0]) if not total_df.empty else 0
    if total == 0:
        return pd.DataFrame(), 0

    limit_rows = min(total, MAX_FETCH_ROWS)
    select_sql = f"SELECT * FROM {loader.table_name} {where_sql} LIMIT ?"
    select_params = params + [limit_rows]
    df = loader.query(select_sql, select_params)

    if total > MAX_FETCH_ROWS:
        current_app.logger.warning(
            "Filtered claim dataset truncated to %s rows (total=%s). Adjust CLAIMS_MAX_QUERY_ROWS if needed.",
            MAX_FETCH_ROWS,
            total,
        )

    return df, total


def _compute_rule_enrichment(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    los = df["los"].fillna(0)
    peer_p90 = df["peer_p90"]
    payment_ratio = df["bpjs_payment_ratio"].fillna(0)
    cost_zscore = df["cost_zscore"].fillna(0)

    if "duplicate_pattern" not in df.columns:
        df["duplicate_pattern"] = False

    duplicate_pattern = df["duplicate_pattern"].fillna(False).astype(bool)

    df["short_stay_high_cost"] = (los <= 1) & (df["amount_claimed"] > peer_p90)
    df["severity_mismatch"] = (df["severity_group"] == "ringan") & (df["amount_claimed"] > peer_p90)
    df["high_cost_full_paid"] = (payment_ratio >= 0.95) & (cost_zscore > 2)

    flag_columns = {
        "short_stay_high_cost": df["short_stay_high_cost"],
        "severity_mismatch": df["severity_mismatch"],
        "high_cost_full_paid": df["high_cost_full_paid"],
        "duplicate_pattern": duplicate_pattern,
    }
    flag_names = list(flag_columns.keys())
    flag_matrix = np.column_stack([flag_columns[name].astype(bool).values for name in flag_names])
    df["flags"] = [
        [flag_names[col_idx] for col_idx, active in enumerate(row) if active]
        for row in flag_matrix
    ]

    weights = {
        "short_stay_high_cost": 0.8,
        "severity_mismatch": 0.7,
        "high_cost_full_paid": 0.5,
        "duplicate_pattern": 0.6,
    }
    rule_score = np.zeros(len(df))
    for flag, weight in weights.items():
        rule_score = np.maximum(rule_score, df[flag].astype(float) * weight)
    df["rule_score"] = rule_score
    return df


def _get_ruleset_version() -> str:
    try:
        return current_app.config.get("RULESET_VERSION", "RULESET_v1")
    except RuntimeError:
        return "RULESET_v1"


def _is_na(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except TypeError:
        return False


def _sanitize_json_value(value: Any) -> Any:
    if _is_na(value):
        return None
    return value


def _to_optional_float(value: Any) -> float | None:
    value = _sanitize_json_value(value)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_optional_int(value: Any) -> int | None:
    value = _sanitize_json_value(value)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_optional_str(value: Any) -> str | None:
    value = _sanitize_json_value(value)
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _to_optional_title(value: Any) -> str | None:
    text = _to_optional_str(value)
    return text.title() if text else text


def _to_optional_date(value: Any) -> str | None:
    value = _sanitize_json_value(value)
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    try:
        ts = pd.to_datetime(value, errors="coerce")
        if pd.isna(ts):
            return None
        return ts.isoformat()
    except Exception:
        text = _to_optional_str(value)
        return text


def _load_or_compute_scores(loader: DataLoader, scorer: MLScorer, force_refresh: bool = False) -> pd.DataFrame:
    scores_path = loader.parquet_dir / SCORES_CACHE_FILENAME
    if not force_refresh:
        scores_from_db = loader.read_table_from_duckdb(SCORES_CACHE_TABLE)
        if scores_from_db is not None and not scores_from_db.empty:
            return scores_from_db
        if scores_path.exists():
            return pd.read_parquet(scores_path)

    df_all = loader.load_claims_normalized()
    scores = scorer.score_dataframe(df_all)
    loader.write_dataframe_to_duckdb(scores, SCORES_CACHE_TABLE, mode="replace")
    scores_path.parent.mkdir(parents=True, exist_ok=True)
    scores.to_parquet(scores_path, index=False)
    _log_qc_snapshot(df_all, scores)
    return scores


def _determine_page_size(filters: Mapping[str, Any]) -> int:
    value = filters.get("page_size") or filters.get("limit")
    return _parse_positive_int(value, DEFAULT_PAGE_SIZE)


def _determine_page(filters: Mapping[str, Any]) -> int:
    return _parse_positive_int(filters.get("page"), 1)


def _parse_positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


def _should_refresh_cache(filters: Mapping[str, Any]) -> bool:
    refresh_flag = filters.get("refresh_cache")
    if isinstance(refresh_flag, bool):
        return refresh_flag
    if isinstance(refresh_flag, str):
        return refresh_flag.lower() in {"1", "true", "yes"}
    return False


def _apply_advanced_filters(df: pd.DataFrame, filters: Mapping[str, Any]) -> pd.DataFrame:
    result = df

    severity = filters.get("severity")
    if severity and "severity_group" in result.columns:
        result = result[result["severity_group"].fillna("").astype(str).str.upper() == severity.upper().strip()]

    service_type = filters.get("service_type")
    if service_type and "service_type" in result.columns:
        result = result[result["service_type"].fillna("").astype(str).str.upper() == service_type.upper().strip()]

    min_risk = _parse_float(filters.get("min_risk_score"))
    if min_risk is not None and "risk_score" in result.columns:
        result = result[result["risk_score"] >= min_risk]

    max_risk = _parse_float(filters.get("max_risk_score"))
    if max_risk is not None and "risk_score" in result.columns:
        result = result[result["risk_score"] <= max_risk]

    min_ml = _parse_float(filters.get("min_ml_score"))
    if min_ml is not None and "ml_score_normalized" in result.columns:
        result = result[result["ml_score_normalized"] >= min_ml]

    facility_class = filters.get("facility_class")
    if facility_class and "facility_class" in result.columns:
        result = result[result["facility_class"].fillna("").astype(str).str.upper() == facility_class.upper().strip()]

    start_date = _parse_date(filters.get("start_date"))
    end_date = _parse_date(filters.get("end_date"))
    if (start_date or end_date) and "admit_dt" in result.columns:
        admit_series = pd.to_datetime(result["admit_dt"], errors="coerce")
        mask = pd.Series(True, index=result.index)
        if start_date:
            mask &= admit_series >= start_date
        if end_date:
            mask &= admit_series <= end_date
        result = result[mask]

    discharge_start = _parse_date(filters.get("discharge_start"))
    discharge_end = _parse_date(filters.get("discharge_end"))
    if (discharge_start or discharge_end) and "discharge_dt" in result.columns:
        discharge_series = pd.to_datetime(result["discharge_dt"], errors="coerce")
        mask = pd.Series(True, index=result.index)
        if discharge_start:
            mask &= discharge_series >= discharge_start
        if discharge_end:
            mask &= discharge_series <= discharge_end
        result = result[mask]

    return result


def _fetch_latest_feedback_map(claim_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not claim_ids:
        return {}
    outcomes = (
        AuditOutcome.query.filter(AuditOutcome.claim_id.in_(claim_ids))
        .order_by(AuditOutcome.claim_id, AuditOutcome.created_at.desc())
        .all()
    )
    latest_map: dict[str, dict[str, Any]] = {}
    for outcome in outcomes:
        if outcome.claim_id not in latest_map:
            latest_map[outcome.claim_id] = outcome.to_dict()
    return latest_map


def _parse_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        parsed = float(value)
        return parsed
    except (TypeError, ValueError):
        return None


def _parse_date(value: Any) -> pd.Timestamp | None:
    if value is None:
        return None
    try:
        ts = pd.to_datetime(str(value), errors="coerce")
        if pd.isna(ts):
            return None
        return ts.normalize()
    except Exception:
        return None


def _log_qc_snapshot(raw_df: pd.DataFrame, scores: pd.DataFrame, top_k: int | None = None) -> dict[str, Any] | None:
    if raw_df.empty or scores.empty:
        return None

    scored_df = raw_df.merge(scores, on="claim_id", how="left")
    scored_df = _compute_rule_enrichment(scored_df)
    scored_df["risk_score"] = scored_df[["rule_score", "ml_score_normalized"]].max(axis=1).fillna(0)

    cap = top_k or QC_TOP_K
    top_df = scored_df.sort_values("risk_score", ascending=False).head(cap)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    summary = {
        "timestamp": timestamp,
        "total_rows": int(len(scored_df)),
        "top_k": int(len(top_df)),
        "amount_claimed_mean": _to_optional_float(scored_df["amount_claimed"].mean()),
        "amount_claimed_top_k_mean": _to_optional_float(top_df["amount_claimed"].mean()),
        "cost_zscore_mean": _to_optional_float(scored_df["cost_zscore"].mean()),
        "cost_zscore_top_k_mean": _to_optional_float(top_df["cost_zscore"].mean()),
        "los_le_1_ratio": _to_optional_float((scored_df["los"] <= 1).mean()),
        "los_le_1_ratio_top_k": _to_optional_float((top_df["los"] <= 1).mean() if len(top_df) else None),
        "risk_score_top_k_mean": _to_optional_float(top_df["risk_score"].mean() if len(top_df) else None),
        "ml_score_top_k_mean": _to_optional_float(top_df["ml_score_normalized"].mean() if len(top_df) else None),
    }

    top_records = top_df[
        [
            "claim_id",
            "province_name",
            "severity_group",
            "risk_score",
            "rule_score",
            "ml_score_normalized",
            "amount_claimed",
            "los",
            "duplicate_pattern",
            "flags",
        ]
    ].to_dict(orient="records")

    log_payload = {
        "summary": summary,
        "top_records": top_records,
    }

    log_dir = Path(QC_LOG_DIRNAME)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"ml_scores_qc_{timestamp}.json"
    log_path.write_text(json.dumps(log_payload, indent=2))
    return log_payload


def _build_response(
    items: list[dict[str, Any]],
    total: int,
    page: int,
    page_size: int,
    ruleset_version: str,
    model_version: str,
) -> dict[str, Any]:
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "model_version": model_version,
        "ruleset_version": ruleset_version,
    }


def _to_optional_list(value: Any) -> list[Any] | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple, np.ndarray)):
        cleaned = [_sanitize_json_value(v) for v in list(value)]
        cleaned = [val for val in cleaned if val is not None]
        return cleaned or []
    single = _sanitize_json_value(value)
    if single is None:
        return []
    return [single]
