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
Contoh awal notebook:
```python
!pip install duckdb pandas scikit-learn joblib

from google.colab import files
uploaded = files.upload()  # pilih claims_normalized.parquet(.gz)

import pandas as pd
df = pd.read_parquet('claims_normalized.parquet')
df.head()
```

## 3. Feature Engineering Sesuai Blueprint
- Gunakan `ml/training/config/features.yaml` sebagai sumber fitur numerik/kategorikal.
- Minimal gunakan:
  - Numerik: `los`, `amount_claimed`, `amount_paid`, `amount_gap`, `comorbidity_count`, `peer_mean`, `peer_p90`, `cost_zscore`.
  - Kategorikal (bila dibutuhkan encoding): `severity_group`, `facility_class`, `province_name`, `service_type`.
- Imputasi missing value, standarize numerik (mis. `StandardScaler`).
- Simpan mapping/encoding bila dipakai (perlu buat inference).

## 4. Training Isolation Forest (Unsupervised MVP)
```python
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
import joblib

numeric_features = [...]
X = df[numeric_features].fillna(0)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

model = IsolationForest(
    n_estimators=200,
    contamination=0.03,  # target: flag 3% klaim teratas
    random_state=42,
)
model.fit(X_scaled)

df['ml_score'] = -model.decision_function(X_scaled)  # skor >0 lebih risk
```

### Tujuan Model
- Skor anomali (`ml_score`) menjadi lapisan tambahan di risk engine.
- 0.03 (3%) diselaraskan dengan policy Top-X auditor.
- Model harus kompatibel dengan pipeline inference lokal (scikit-learn >=1.3).

## 5. Evaluasi & Analitik
- Distribusi skor: `df['ml_score'].describe()`.
- Korelasi dengan rule-based flags jika tersedia (`rule_short_stay`, etc.).
- Visualisasi: histogram skor, scatter vs `cost_zscore`, heatmap provinsi/RS.
- Simpan sample klaim high-score (untuk review auditor).

## 6. Export Artefak
```python
joblib.dump(model, 'isolation_forest_v1.pkl')
joblib.dump(scaler, 'scaler_v1.pkl')
```

Metadata:
```python
import json, datetime

meta = {
    "model_name": "isolation_forest",
    "model_version": "iso_v1",
    "trained_on": "claims_normalized",
    "train_rows": len(df),
    "contamination": 0.03,
    "features": numeric_features,
    "prepared_by": "<nama>",
    "train_timestamp": datetime.datetime.utcnow().isoformat(),
    "colab_notebook": "<link notebook>",
}

with open('model_meta.json', 'w') as f:
    json.dump(meta, f, indent=2)
```

Download:
```python
files.download('isolation_forest_v1.pkl')
files.download('scaler_v1.pkl')
files.download('model_meta.json')
```

## 7. Sinkronisasi ke Repo Lokal
1. Taruh artefak di `ml/artifacts/`:
   ```
   ml/artifacts/isolation_forest_v1.pkl
   ml/artifacts/scaler_v1.pkl
   ml/artifacts/model_meta.json
   ```
2. Catat di checkpoint (tanggal, parameter, link notebook).
3. Pastikan `.gitignore` tidak mengecualikan file artefak (boleh commit metadata + model bila ukuran wajar atau gunakan storage terpisah).

## 8. Integrasi dengan Backend
- Buat modul inference (`ml/inference/scorer.py`) yang:
  - Load scaler & model dari `ml/artifacts/`.
  - Ambil fitur dari `claims_normalized` via `DataLoader`.
  - Hasilkan `ml_score` + `model_version`.
- Simpan skor ke tabel/Parquet (mis. `claims_ml_scores.parquet`) atau langsung injeksi ke API response.
- API `GET /claims/high-risk` menggabungkan rule score dan `ml_score`.
- Pastikan response menyertakan `ruleset_version` & `model_version`.

## 9. Roadmap Supervised (kelak ada label)
- Tambah pipeline training klasifikasi (probabilistic risk).
- Output: probabilitas fraud, metrics (ROC-AUC, PR-AUC), calibration info.
- Compose dengan rules dan anomali untuk risk score final.

## 10. Monitoring & Log
- Simpan summary training (skor top-k, distribusi, parameter) di `dev_checkpoint`.
- Siapkan script monitoring (nanti) untuk membandingkan distribusi skor baru vs baseline.

Dengan alur ini, Colab menjadi tempat training, sedangkan repo lokal fokus memuat data (ETL) dan menjalankan inference API. Pastikan artefak yang diunduh dari Colab selalu kompatibel dengan pipeline lokal (versi paket, schema fitur).
