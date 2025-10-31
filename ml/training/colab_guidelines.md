# Panduan Training Model di Google Colab

Panduan ini memayungi seluruh tujuan ML di Casemind AI:

- **Risk Engine**: model ML menghasilkan skor anomali/risiko untuk dilapis dengan rule-based flags, sehingga auditor mendapat prioritas klaim (target top 3–5%).
- **Audit Copilot**: skor & fitur klaim dipakai dalam payload LLM untuk menyusun ringkasan audit/pertanyaan lanjutan.
- **Analitik Wilayah/Segmen**: agregasi high-risk per provinsi/RS memanfaatkan skor ML + rules.
- **Roadmap Supervised**: struktur data memastikan kita siap bertransisi ke model berlabel ketika outcome audit tersedia.

Karena resource training dijalankan di Colab (GPU/CPU cloud), repositori lokal fokus pada ETL, inference, dan integrasi API. Berikut langkah training di Colab beserta artefak yang harus dibawa kembali.

## 1. Dataset Input
1. Jalankan ETL lokal:
   ```bash
   python pipelines/claims_normalized/build_claims_normalized.py
   ```
   Output: `instance/data/claims_normalized.parquet` (≈1.18 juta klaim).

2. Opsional: kompres agar upload cepat:
   ```bash
   gzip instance/data/claims_normalized.parquet
   ```

3. Upload ke Colab:
   - Via `files.upload()` (maks 100MB) atau
   - Taruh di Google Drive lalu `drive.mount('/content/drive')`.

## 2. Setup Notebook
Contoh notebook lengkap (training + ekspor artefak):

```python
!pip install duckdb pandas scikit-learn joblib

import pandas as pd
from google.colab import files

uploaded = files.upload()  # upload claims_normalized.parquet (atau .gz)

df = pd.read_parquet('claims_normalized.parquet')
print(df.head())
print(df.shape)

# inspeksi missing values (opsional tapi disarankan)
print(df.isna().sum().sort_values(ascending=False).head(10))

numeric_features = [
    "los", "amount_claimed", "amount_paid", "amount_gap",
    "comorbidity_count", "peer_mean", "peer_p90", "cost_zscore",
]
categ_features = ["severity_group", "facility_class", "province_name", "service_type"]

X_num = df[numeric_features].fillna(0)
X_cat = pd.get_dummies(df[categ_features].fillna("UNK"))
X = pd.concat([X_num, X_cat], axis=1)

from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
import joblib

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

model = IsolationForest(
    n_estimators=200,
    contamination=0.03,
    random_state=42,
)
model.fit(X_scaled)

df["ml_score"] = -model.decision_function(X_scaled)
print(df["ml_score"].describe())

# Analisis cepat
print(df[["cost_zscore", "ml_score"]].corr())
top_claims = df.nlargest(10, "ml_score")
display(top_claims[["claim_id", "los", "amount_claimed", "cost_zscore", "ml_score"]])

# Simpan artefak
joblib.dump(model, "isolation_forest_iso_v1.pkl")
joblib.dump(scaler, "scaler_iso_v1.pkl")
X.columns.to_series().to_json("feature_columns.json", orient="values")

import json, datetime

meta = {
    "model_name": "isolation_forest",
    "model_version": "iso_v1",
    "trained_on": "claims_normalized",
    "train_rows": int(len(df)),
    "contamination": 0.03,
    "numeric_features": numeric_features,
    "categorical_features": categ_features,
    "feature_columns": list(X.columns),
    "prepared_by": "<nama>",
    "train_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    "colab_notebook": "<link notebook>",
}
with open("model_meta.json", "w") as f:
    json.dump(meta, f, indent=2)

from google.colab import files
files.download("isolation_forest_iso_v1.pkl")
files.download("scaler_iso_v1.pkl")
files.download("feature_columns.json")
files.download("model_meta.json")
```

### Tujuan Model
- `ml_score` menjadi lapisan tambahan di risk engine.
- 0.03 (3%) diselaraskan dengan kapasitas audit (Top-X policy).
- Artefak kompatibel dengan pipeline inference lokal (scikit-learn ≥ 1.3).

## 5. Evaluasi & Analitik
- Distribusi skor: `df['ml_score'].describe()`.
- Korelasi dengan rule-based flags jika tersedia (`rule_short_stay`, etc.).
- Visualisasi: histogram skor, scatter vs `cost_zscore`, heatmap provinsi/RS.
- Catat kolom dengan nilai hilang signifikan (gunakan `df.isna().sum()`), dokumentasikan di checkpoint jika perlu.
- Simpan sample klaim high-score (untuk review auditor).

## 6. Export Artefak (wajib dibawa pulang)

Artefak wajib:
- `isolation_forest_iso_v1.pkl`
- `scaler_iso_v1.pkl`
- `feature_columns.json`
- `model_meta.json`

## 7. Sinkronisasi ke Repo Lokal
1. Taruh artefak di `ml/artifacts/`:
   ```
   ml/artifacts/isolation_forest_iso_v1.pkl
   ml/artifacts/scaler_iso_v1.pkl
   ml/artifacts/feature_columns.json
   ml/artifacts/model_meta.json
   ```
2. Catat di checkpoint (tanggal, parameter, link notebook).
3. Pastikan `.gitignore` tidak mengecualikan file artefak (boleh commit metadata + model bila ukuran wajar atau gunakan storage terpisah).

## 8. Integrasi dengan Backend
- Buat modul inference (`ml/inference/scorer.py`) yang:
  - Load scaler & model dari `ml/artifacts/`.
  - Ambil fitur dari `claims_normalized` via `DataLoader`.
  - Hasilkan `ml_score` + `model_version`.
- Contoh implementasi inference tersedia (lihat `ml/inference/scorer.py`), misalnya:
  ```python
  from ml.inference.scorer import MLScorer

  scorer = MLScorer()
  df_scores = scorer.score_claims(limit=1000)
  # df_scores -> kolom: claim_id, ml_score, ml_score_normalized, model_version
  ```
- Simpan skor ke tabel/Parquet (mis. `claims_ml_scores.parquet`) atau langsung injeksi ke API response.
- API `GET /claims/high-risk` menggabungkan rule score dan `ml_score`.
- Pastikan response menyertakan `ruleset_version` & `model_version`.

### Contoh modul inference lokal

Repo ini menyediakan contoh end-to-end (`ml/inference/scorer.py`). Intinya:

```python
from ml.inference.scorer import MLScorer

scorer = MLScorer()
scores_df = scorer.score(limit=5)
print(scores_df)
```

Output:
- `claim_id`
- `ml_score`
- `ml_score_normalized`
- `model_version`

Service (mis. `app/services/risk_scoring.py`) menggabungkan skor ini dengan rule-based score sehingga auditor melihat prioritas final (`risk_score = max(rule_score, ml_score_normalized)` atau formula lain).

## 9. Roadmap Supervised (kelak ada label)
- Tambah pipeline training klasifikasi (probabilistic risk).
- Output: probabilitas fraud, metrics (ROC-AUC, PR-AUC), calibration info.
- Compose dengan rules dan anomali untuk risk score final.

## 10. Monitoring & Log
- Simpan summary training (skor top-k, distribusi, parameter) di `dev_checkpoint`.
- Siapkan script monitoring (nanti) untuk membandingkan distribusi skor baru vs baseline.

Dengan alur ini, Colab menjadi tempat training, sedangkan repo lokal fokus memuat data (ETL) dan menjalankan inference API. Pastikan artefak yang diunduh dari Colab selalu kompatibel dengan pipeline lokal (versi paket, schema fitur).
