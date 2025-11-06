from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flask import current_app

DEFAULT_RISK_MIN = 0.7
DEFAULT_LOS_RATIO_MIN = 0.05


@dataclass
class Thresholds:
    risk_score_min: float
    los_le_1_ratio_min: float

    def to_dict(self) -> dict[str, float]:
        return {
            "risk_score_min": self.risk_score_min,
            "los_le_1_ratio_min": self.los_le_1_ratio_min,
        }


def _resolve_summary_path() -> Path:
    custom_path = current_app.config.get("QC_SUMMARY_PATH") or os.getenv("QC_SUMMARY_PATH")
    if custom_path:
        candidate = Path(custom_path)
        if not candidate.is_absolute():
            candidate = Path(current_app.root_path).parent / candidate
        return candidate
    return Path(current_app.instance_path) / "logs" / "ml_scores_qc_summary.json"


def _thresholds_from_config() -> Thresholds:
    risk_min = float(current_app.config.get("QC_ALERT_MIN_RISK_SCORE", os.getenv("QC_ALERT_MIN_RISK_SCORE", DEFAULT_RISK_MIN)))
    los_min = float(current_app.config.get("QC_ALERT_MIN_LOS_RATIO", os.getenv("QC_ALERT_MIN_LOS_RATIO", DEFAULT_LOS_RATIO_MIN)))
    return Thresholds(risk_score_min=risk_min, los_le_1_ratio_min=los_min)


def _load_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"QC summary not found at {path}")
    with path.open() as f:
        return json.load(f)


def _extract_latest_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    latest_snapshot = payload.get("latest_snapshot") or {}
    if latest_snapshot and any(value is not None for value in latest_snapshot.values()):
        return latest_snapshot
    snapshots = payload.get("snapshots") or []
    for snap in reversed(snapshots):
        summary = (snap or {}).get("summary") or {}
        if summary:
            return summary
    return {}


def _convert_pairs(pairs: list[list[Any]] | list[tuple[Any, Any]] | None) -> list[dict[str, Any]]:
    if not pairs:
        return []
    converted = []
    for item in pairs:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            converted.append({"name": item[0], "count": item[1]})
    return converted


def get_qc_status() -> dict[str, Any]:
    thresholds = _thresholds_from_config()
    summary_path = _resolve_summary_path()

    try:
        payload = _load_summary(summary_path)
    except FileNotFoundError:
        return {
            "status": "no_data",
            "message": "QC summary belum tersedia. Jalankan 'python -m ml.pipelines.qc_summary' setelah refresh skor ML.",
            "thresholds": thresholds.to_dict(),
        }

    latest_summary = _extract_latest_snapshot(payload)
    if not latest_summary:
        return {
            "status": "no_data",
            "message": "QC summary kosong. Pastikan pipeline refresh menulis log.",
            "thresholds": thresholds.to_dict(),
        }

    risk_mean = latest_summary.get("risk_score_top_k_mean")
    los_ratio = latest_summary.get("los_le_1_ratio_top_k")

    alerts: list[str] = []
    if isinstance(risk_mean, (int, float)) and risk_mean < thresholds.risk_score_min:
        alerts.append(f"risk_score_top_k_mean {risk_mean:.2f} < {thresholds.risk_score_min:.2f}")
    if isinstance(los_ratio, (int, float)) and los_ratio < thresholds.los_le_1_ratio_min:
        alerts.append(f"los_le_1_ratio_top_k {los_ratio:.2f} < {thresholds.los_le_1_ratio_min:.2f}")
    status = "alert" if alerts else "ok"

    metrics = {
        "timestamp": latest_summary.get("timestamp"),
        "total_rows": latest_summary.get("total_rows"),
        "top_k": latest_summary.get("top_k"),
        "risk_score_top_k_mean": risk_mean,
        "ml_score_top_k_mean": latest_summary.get("ml_score_top_k_mean"),
        "los_le_1_ratio_top_k": los_ratio,
        "amount_claimed_top_k_mean": latest_summary.get("amount_claimed_top_k_mean"),
    }

    return {
        "status": status,
        "message": " ; ".join(alerts) if alerts else "Semua metrik dalam ambang normal.",
        "thresholds": thresholds.to_dict(),
        "metrics": metrics,
        "top_provinces": _convert_pairs(payload.get("top_province_in_top_k")),
        "top_severity": _convert_pairs(payload.get("top_severity_in_top_k")),
        "top_flags": _convert_pairs(payload.get("top_flags_in_top_k")),
    }
