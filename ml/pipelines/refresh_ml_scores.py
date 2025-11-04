"""
CLI script untuk merefresh cache skor ML dan mencatat QC snapshot.

Usage:
    python -m ml.pipelines.refresh_ml_scores --top-k 50 --refresh
"""

from __future__ import annotations

import argparse

from ml.common.data_access import DataLoader
from ml.inference.scorer import MLScorer

from app.services import risk_scoring


def refresh_scores(top_k: int | None = None) -> None:
    loader = DataLoader()
    scorer = MLScorer()

    df_all = loader.load_claims_normalized()
    scores = scorer.score_dataframe(df_all)

    loader.write_dataframe_to_duckdb(scores, risk_scoring.SCORES_CACHE_TABLE, mode="replace")

    parquet_path = loader.parquet_dir / risk_scoring.SCORES_CACHE_FILENAME
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    scores.to_parquet(parquet_path, index=False)

    risk_scoring._log_qc_snapshot(df_all, scores, top_k=top_k)

    print(f"Cached {len(scores)} rows to {parquet_path} and DuckDB table '{risk_scoring.SCORES_CACHE_TABLE}'.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh cached ML scores and log QC snapshot.")
    parser.add_argument("--top-k", type=int, default=None, help="Jumlah klaim teratas untuk disimpan di QC log.")
    args = parser.parse_args()

    refresh_scores(top_k=args.top_k)


if __name__ == "__main__":
    main()
