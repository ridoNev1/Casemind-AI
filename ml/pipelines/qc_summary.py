"""
Generate summary statistik dari log QC skor ML.

Usage:
    python -m ml.pipelines.qc_summary --logs-dir instance/logs --output instance/logs/ml_scores_qc_summary.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class QCSnapshot:
    timestamp: str
    summary: dict
    top_records: list[dict]


def load_snapshots(log_dir: Path) -> list[QCSnapshot]:
    snapshots: list[QCSnapshot] = []
    for path in sorted(log_dir.glob("ml_scores_qc_*.json")):
        payload = json.loads(path.read_text())
        snapshots.append(
            QCSnapshot(
                timestamp=payload.get("summary", {}).get("timestamp", path.stem.split("_")[-1]),
                summary=payload.get("summary", {}),
                top_records=payload.get("top_records", []),
            )
        )
    return snapshots


def aggregate_snapshots(snapshots: Iterable[QCSnapshot]) -> dict:
    snapshots = list(snapshots)
    if not snapshots:
        return {"snapshots": []}

    latest = snapshots[-1]

    def mean_from_snapshots(key: str) -> float | None:
        values = [snap.summary.get(key) for snap in snapshots if isinstance(snap.summary.get(key), (int, float))]
        if not values:
            return None
        return sum(values) / len(values)

    severity_counter: Counter[str] = Counter()
    province_counter: Counter[str] = Counter()
    flag_counter: Counter[str] = Counter()

    for snap in snapshots:
        for record in snap.top_records:
            severity_counter.update([record.get("severity_group")])
            province_counter.update([record.get("province_name")])
            flag_counter.update(record.get("flags", []))

    return {
        "total_snapshots": len(snapshots),
        "latest_snapshot": latest.summary,
        "averages": {
            "amount_claimed_mean": mean_from_snapshots("amount_claimed_mean"),
            "amount_claimed_top_k_mean": mean_from_snapshots("amount_claimed_top_k_mean"),
            "cost_zscore_mean": mean_from_snapshots("cost_zscore_mean"),
            "cost_zscore_top_k_mean": mean_from_snapshots("cost_zscore_top_k_mean"),
            "los_le_1_ratio": mean_from_snapshots("los_le_1_ratio"),
            "los_le_1_ratio_top_k": mean_from_snapshots("los_le_1_ratio_top_k"),
        },
        "top_severity_in_top_k": severity_counter.most_common(10),
        "top_province_in_top_k": province_counter.most_common(10),
        "top_flags_in_top_k": flag_counter.most_common(10),
        "snapshots": [
            {
                "timestamp": snap.timestamp,
                "summary": snap.summary,
                "top_record_count": len(snap.top_records),
            }
            for snap in snapshots
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate QC summary reports from ML score logs.")
    parser.add_argument("--logs-dir", type=Path, default=Path("instance/logs"), help="Direktori sumber log QC.")
    parser.add_argument("--output", type=Path, default=Path("instance/logs/ml_scores_qc_summary.json"), help="Path output summary JSON.")
    args = parser.parse_args()

    if not args.logs_dir.exists():
        raise FileNotFoundError(f"Logs directory not found: {args.logs_dir}")

    snapshots = load_snapshots(args.logs_dir)
    summary = aggregate_snapshots(snapshots)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2))
    print(f"QC summary saved to {args.output} (snapshots={summary.get('total_snapshots', 0)})")


if __name__ == "__main__":
    main()
