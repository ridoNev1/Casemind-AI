"""
Baseline scaffold for ML training pipeline.

Current behaviour:
- load claims_normalized via DataLoader
- select subset of features from config
- print head / describe to validate pipeline

Extend this script to include actual training, evaluation, and artifact export.
"""

from __future__ import annotations

import yaml
from pathlib import Path

import pandas as pd

from ml.common.data_access import DataLoader

FEATURE_CONFIG_PATH = Path("ml/training/config/features.yaml")


def load_feature_config(path: Path = FEATURE_CONFIG_PATH) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Feature config not found at {path}")
    with path.open() as f:
        return yaml.safe_load(f)


def prepare_features(df: pd.DataFrame, feature_cfg: dict) -> pd.DataFrame:
    """Select numeric + categorical features based on config."""
    columns = (feature_cfg.get("numeric_features") or []) + (feature_cfg.get("categorical_features") or [])
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise KeyError(f"Missing columns in dataframe: {missing}")
    return df[columns]


def main(sample_size: int = 1000) -> None:
    loader = DataLoader()
    feature_cfg = load_feature_config()

    df = loader.load_claims_normalized(limit=sample_size)
    features = prepare_features(df, feature_cfg)

    print("Sample features:")
    print(features.head())
    print("\nSummary:")
    print(features.describe(include="all"))


if __name__ == "__main__":
    main()
