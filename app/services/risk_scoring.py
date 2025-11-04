from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import json
import numpy as np
import pandas as pd
from flask import current_app

from ml.common.data_access import DataLoader
from ml.inference.scorer import MLScorer

DEFAULT_PAGE_SIZE = 50
SCORES_CACHE_FILENAME = "claims_ml_scores.parquet"
SCORES_CACHE_TABLE = "claims_ml_scores"
QC_LOG_DIRNAME = "instance/logs"
QC_TOP_K = 50


def get_high_risk_claims(filters: Mapping[str, Any]) -> dict[str, Any]:
    loader = DataLoader()
    scorer = MLScorer()

    data_filters = _build_data_filters(filters)
    df = loader.load_claims_normalized(filters=data_filters)
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
    df = df.sort_values("risk_score", ascending=False)

    page_size = _determine_page_size(filters)
    page = _determine_page(filters)
    start = (page - 1) * page_size
    end = start + page_size
    paged_df = df.iloc[start:end].copy()

    ruleset_version = _get_ruleset_version()

    results: list[dict[str, Any]] = []
    for row in paged_df.itertuples(index=False):
        results.append(
            {
                "claim_id": row.claim_id,
                "province_name": row.province_name,
                "dx_primary_code": row.dx_primary_code,
                "severity_group": row.severity_group,
                "service_type": getattr(row, "service_type", None),
                "facility_class": getattr(row, "facility_class", None),
                "amount_claimed": _to_optional_float(row.amount_claimed),
                "amount_paid": _to_optional_float(row.amount_paid),
                "cost_zscore": _to_optional_float(row.cost_zscore),
                "los": _to_optional_int(row.los),
                "bpjs_payment_ratio": _to_optional_float(row.bpjs_payment_ratio),
                "peer": {
                    "mean": _to_optional_float(row.peer_mean),
                    "p90": _to_optional_float(row.peer_p90),
                },
                "flags": row.flags,
                "rule_score": _to_optional_float(row.rule_score),
                "ml_score": _to_optional_float(row.ml_score),
                "ml_score_normalized": _to_optional_float(row.ml_score_normalized),
                "risk_score": _to_optional_float(row.risk_score),
                "model_version": row.model_version,
                "ruleset_version": ruleset_version,
            }
        )

    return _build_response(
        results,
        total=len(df),
        page=page,
        page_size=page_size,
        ruleset_version=ruleset_version,
        model_version=scorer.model_version,
    )


def _build_data_filters(filters: Mapping[str, Any]) -> dict[str, object]:
    province = filters.get("province")
    dx = filters.get("dx")

    data_filters: dict[str, object] = {}
    if province:
        data_filters["province_name"] = province.upper()
    if dx:
        data_filters["dx_primary_code"] = dx.upper()
    return data_filters


def _compute_rule_enrichment(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    los = df["los"].fillna(0)
    peer_p90 = df["peer_p90"]
    payment_ratio = df["bpjs_payment_ratio"].fillna(0)
    cost_zscore = df["cost_zscore"].fillna(0)

    df["short_stay_high_cost"] = (los <= 1) & (df["amount_claimed"] > peer_p90)
    df["severity_mismatch"] = (df["severity_group"] == "ringan") & (df["amount_claimed"] > peer_p90)
    df["high_cost_full_paid"] = (payment_ratio >= 0.95) & (cost_zscore > 2)

    flag_columns = {
        "short_stay_high_cost": df["short_stay_high_cost"],
        "severity_mismatch": df["severity_mismatch"],
        "high_cost_full_paid": df["high_cost_full_paid"],
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


def _to_optional_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_optional_int(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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

    return result


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


def _log_qc_snapshot(raw_df: pd.DataFrame, scores: pd.DataFrame, top_k: int | None = None) -> None:
    if raw_df.empty or scores.empty:
        return

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
