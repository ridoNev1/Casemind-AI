"""Utilities to apply trained ML model (Isolation Forest) on claims_normalized."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import joblib
import pandas as pd

from ml.common.data_access import DataLoader

ARTIFACT_DIR = Path("ml/artifacts")
MODEL_FILE = ARTIFACT_DIR / "isolation_forest_iso_v1.pkl"
SCALER_FILE = ARTIFACT_DIR / "scaler_iso_v1.pkl"
FEATURE_COLUMNS_FILE = ARTIFACT_DIR / "feature_columns.json"
MODEL_META_FILE = ARTIFACT_DIR / "model_meta.json"


class MLScorer:
    """Load model artefak dan menghasilkan skor anomali klaim."""

    def __init__(self) -> None:
        if not MODEL_FILE.exists() or not SCALER_FILE.exists():
            raise FileNotFoundError(
                "Model/scaler artefak tidak ditemukan. Pastikan file hasil training Colab "
                "tersimpan di ml/artifacts/."
            )

        self.model = joblib.load(MODEL_FILE)
        self.scaler = joblib.load(SCALER_FILE)

        if FEATURE_COLUMNS_FILE.exists():
            self.feature_columns = pd.read_json(FEATURE_COLUMNS_FILE, typ="series", orient="values").tolist()
        else:
            self.feature_columns = None

        if MODEL_META_FILE.exists():
            self.model_meta = pd.read_json(MODEL_META_FILE, typ="series")
            self.model_version = self.model_meta.get("model_version", "unknown")
        else:
            self.model_meta = None
            self.model_version = "unknown"

        # default fitur basic sesuai config
        self.numeric_features = [
            "los",
            "amount_claimed",
            "amount_paid",
            "amount_gap",
            "comorbidity_count",
            "peer_mean",
            "peer_p90",
            "cost_zscore",
        ]
        self.categorical_features = [
            "severity_group",
            "facility_class",
            "province_name",
            "service_type",
        ]

        if self.model_meta is not None:
            self.numeric_features = self.model_meta.get("numeric_features", self.numeric_features)
            self.categorical_features = self.model_meta.get("categorical_features", self.categorical_features)

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        missing_numeric = [col for col in self.numeric_features if col not in df.columns]
        if missing_numeric:
            raise KeyError(f"Kolom numerik hilang pada dataframe inference: {missing_numeric}")

        X_num = df[self.numeric_features].fillna(0)
        X_num_scaled = pd.DataFrame(
            self.scaler.transform(X_num),
            columns=self.numeric_features,
            index=df.index,
        )

        if self.categorical_features:
            X_cat = pd.get_dummies(df[self.categorical_features].fillna("UNK"))
            X = pd.concat([X_num_scaled, X_cat], axis=1)
        else:
            X = X_num_scaled

        if self.feature_columns:
            # Pastikan kolom sesuai training (tambahkan kolom kosong jika hilang)
            for col in self.feature_columns:
                if col not in X.columns:
                    X[col] = 0
            unexpected_cols = [col for col in X.columns if col not in self.feature_columns]
            if unexpected_cols:
                X = X.drop(columns=unexpected_cols)
            X = X[self.feature_columns]

        return X

    def score(self, limit: Optional[int] = None) -> pd.DataFrame:
        loader = DataLoader()
        df = loader.load_claims_normalized(limit=limit)

        return self.score_dataframe(df)

    def score_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Score klaim menggunakan dataframe yang sudah dimuat di luar DataLoader.

        Args:
            df: DataFrame dengan kolom sesuai numeric_features/categorical_features.

        Returns:
            DataFrame kolom: claim_id, ml_score, ml_score_normalized, model_version.
        """
        if df.empty:
            return pd.DataFrame(columns=["claim_id", "ml_score", "ml_score_normalized", "model_version"])

        X = self._prepare_features(df)
        scores = -self.model.decision_function(X)
        df_scores = pd.DataFrame(
            {
                "claim_id": df["claim_id"].values,
                "ml_score": scores,
            },
            index=df.index,
        )

        min_score, max_score = df_scores["ml_score"].min(), df_scores["ml_score"].max()
        df_scores["ml_score_normalized"] = (df_scores["ml_score"] - min_score) / (max_score - min_score + 1e-8)
        df_scores["model_version"] = self.model_version
        return df_scores


if __name__ == "__main__":
    scorer = MLScorer()
    sample = scorer.score(limit=5)
    print(sample)
