# Casemind Claims Backend

Repositori ini merupakan tulang punggung risk engine Casemind AI: mulai dari ETL
klaim, training model anomali, caching skor rules + ML, API risk scoring,
hingga integrasi agentic AI (audit copilot, validator, simulasi klaim).

---

## Resource penting pengembangan bisa cek di :

1. Folder `/docs`
2. Folder `/resource`

## 1. Arsitektur & Alur Sistem

### 1.1 ETL `claims_normalized`

- Pipeline: `pipelines/claims_normalized/`
  1. **Staging** (`staging.sql`) memuat CSV FKRTL, metadata RS, wilayah, dsb. ke DuckDB.
  2. **Transform** (`transform.sql`): hitung LOS, amount gap, `peer_key`, `peer_mean/p90/std`, `cost_zscore`; label fasilitas dan severity.
  3. **Output**: menyimpan tabel `claims_normalized` & `claims_scored` ke `instance/analytics.duckdb` serta Parquet `instance/data/claims_normalized.parquet`.
- Backlog: hash + salt `patient_key`, hitung flag `duplicate_pattern`, log ETL run.

### 1.2 Training Anomali (Isolation Forest)

- Notebook lokal: `ml/training/notebooks/deteksi_anomali_unsupervised.ipynb` (lihat panduan `ml/training/local_training_guide.md`).
- Fitur mengacu ke `ml/training/config/features.yaml` (numerik + kategori baseline).
- Artefak disimpan ke `ml/artifacts/`:
  - `isolation_forest_iso_v1.pkl`
  - `scaler_iso_v1.pkl`
  - `feature_columns.json`
  - `model_meta.json` (metadata training).

### 1.3 Refresh Skor & Quality Check

- Jalankan setelah artefak diperbarui:
  ```bash
  source .venv/bin/activate
  python -m ml.pipelines.refresh_ml_scores --top-k 50
  python -m ml.pipelines.qc_summary
  ```
- Output:
  - Cache ML: `instance/data/claims_ml_scores.parquet` & tabel DuckDB `claims_ml_scores`.
  - Log QC per run: `instance/logs/ml_scores_qc_<timestamp>.json`.
  - Ringkasan agregat: `instance/logs/ml_scores_qc_summary.json`.
- Skrip helper untuk cron: `ops/scripts/refresh_ml_scores.sh`.
- Runbook operasional: `docs/ops/runbook_risk_scoring.md`.

### 1.4 Risk Scoring API

- Service: `app/services/risk_scoring.py`
  - Muat klaim via `DataLoader` + skor ML dari cache.
  - Hitung flag rules (`short_stay_high_cost`, `severity_mismatch`, `high_cost_full_paid`; _todo_ `duplicate_pattern`).
  - `risk_score = max(rule_score, ml_score_normalized)`.
  - Mendukung filter lanjutan (`province`, `dx`, `severity`, `service_type`, `facility_class`, `start_date`, `end_date`, `min/max_risk_score`, `min_ml_score`), pagination, dan `refresh_cache`.
- Endpoint utama: `GET /claims/high-risk` (JWT protected).
- Dokumentasi: Swagger `app/api/docs/spec.py`.

### 1.5 Agentic AI

- **Audit Copilot (LLM komunikasi)** – roadmap endpoint `GET /claims/{id}/summary` untuk meramu ringkasan audit & pertanyaan tindak lanjut.
- **Feedback Loop** – simpan hasil audit ke tabel `audit_outcome`, menjadi label untuk tuning rules + model supervised.
- **Validator Agent** – baca `ml_scores_qc_summary.json`, pantau tren Top-K, trigger alert bila terjadi drift.
- **Data Simulation** – agen LLM menghasilkan klaim sintetis tiap 10–30 detik (`docs/ops/data_simulation.md`) untuk uji streaming.

---

## 2. Quick Start

### 2.1 Setup Lingkungan

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # isi variabel yang dibutuhkan
```

### 2.2 Jalankan ETL

```bash
source .venv/bin/activate
python pipelines/claims_normalized/build_claims_normalized.py
```

### 2.3 Training Model (opsional)

Ikuti `ml/training/local_training_guide.md` untuk menjalankan notebook IsoForest dan menyimpan artefak.

### 2.4 Refresh Skor & QC

```bash
python -m ml.pipelines.refresh_ml_scores --top-k 50
python -m ml.pipelines.qc_summary
```

### 2.5 Jalankan API

```bash
flask --app wsgi.py run
```

Contoh call: `GET /claims/high-risk?service_type=RITL&severity=sedang&page_size=5`
(Authorization `Bearer <token>`).

### 2.6 Simulasi Klaim (opsional)

Lihat `docs/ops/data_simulation.md` untuk menjalankan agen LLM yang men-stream klaim sintetis.

---

## 3. Operasional & Monitoring

| Kegiatan         | Perintah                                                   | Referensi        |
| ---------------- | ---------------------------------------------------------- | ---------------- |
| Refresh skor ML  | `python -m ml.pipelines.refresh_ml_scores --top-k 50`      | Runbook §Refresh |
| QC summary       | `python -m ml.pipelines.qc_summary`                        | Runbook §Refresh |
| Cron helper      | `ops/scripts/refresh_ml_scores.sh`                         | Runbook          |
| Monitoring log   | `instance/logs/ml_scores_qc_summary.json`                  | Runbook          |
| Dok. risk engine | `docs/dev_checkpoint/checkpoint_3_risk_api_integration.md` | Checkpoint       |
| Simulasi klaim   | `docs/ops/data_simulation.md`                              | Simulation       |

Backlog utama:

1. Hash + salt `patient_key`, hitung `duplicate_pattern`, integrasikan ke rules.
2. Ganti mock `/reports/severity-mismatch` & `/reports/duplicates` dengan query DuckDB.
3. Simpan metadata ruleset/model (`ruleset_versions`).
4. Integrasi cron/CI dan bangun dashboard (heatmap provinsi, proporsi flag).
5. Implementasi endpoint ringkasan audit + feedback loop.

---

## 4. Struktur Direktori

```
app/                    # Flask services, API, auth
  api/
  services/
  ...
docs/ops/               # Runbook & data simulation guide
docs/dev_checkpoint/         # Catatan perkembangan (Checkpoint 1–3)
ml/
  artifacts/
  training/
  inference/
  pipelines/
pipelines/claims_normalized/  # ETL scripts
resource/               # Dokumen teknis & patch notes (tidak berisi PII)
instance/               # DuckDB, Parquet, logs (ignored git)
tests/                  # Pytest
```

---

## 5. Lampiran Dokumen Penting

- **Teknis Data & ML/LLM**: `resource/docs_teknis/data-recipes.md`, `resource/docs_teknis/ml-llm-recipes.md`
- **Patch narasi**: `resource/apss_update_patch_1.1.md`
- **Sample data overview (private)**: `resource/private_bpjs_data/dataset_overview.md` (FKRTL, kepesertaan, faskes; summary kolom dan ukuran dataset)
- **Sample CSV (private)**: `resource/private_bpjs_data/raw_cleaned/` _(tidak di-commit; data klaim BPJS sample, gunakan hanya untuk pengujian internal)_
- **Sample reference (public)**: `resource/public_data_resources/` (ICD-10/9, master RS, wilayah)
- **Runbook operasional**: `docs/ops/runbook_risk_scoring.md`
- **Simulasi data**: `docs/ops/data_simulation.md`
- **Panduan training lokal**: `ml/training/local_training_guide.md`

Dengan alur ini, seluruh tim (BE, FE, auditor, ops) memiliki referensi jelas:
bagaimana data masuk, model dilatih, skor di-refresh, API melayani permintaan,
agent LLM membantu audit, dan bagaimana sistem dipantau.
