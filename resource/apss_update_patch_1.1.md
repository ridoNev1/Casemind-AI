# APSS Update Patch 1.1 — Skenario End-to-End Risk Engine + Agentic AI

Tanggal: 15 Nov 2025  
PIC: Rido Maulana (user)

Dokumen ini menjadi acuan menyeluruh mengenai perubahan arsitektur, alur data, integrasi agen LLM, serta penambahan simulasi data yang mendukung aplikasi audit BPJS Casemind AI.

---

## 1. Gambaran Umum

Tujuan utama patch 1.1:

1. **Memperkuat pipeline risk scoring** (ETL → ML scoring → API) agar siap dipakai tim auditor.  
2. **Menambahkan skenario agentic AI** — meliputi audit copilot, aggregator feedback, validator skor, dan simulasi klaim realtime.  
3. **Mendokumentasikan jalur operasional** sehingga tim FE dan ops dapat melanjutkan pengembangan dengan referensi tunggal.

---

## 2. Arsitektur Data & Pipeline

### 2.1 ETL `claims_normalized`
- Lokasi pipeline: `pipelines/claims_normalized/`.  
- Tahapan:
  1. **Staging**: membaca CSV FKRTL/metadata ke DuckDB.  
  2. **Transform**: menghitung LOS, amount gap, `peer_key`, `peer_mean/p90/std`, `cost_zscore`. Menambah label fasilitas, severity, service type.  
  3. **Output**: menulis ke DuckDB (`instance/analytics.duckdb`) dan Parquet (`instance/data/claims_normalized.parquet`).
- **Pekerjaan lanjut**: hash + salt `patient_key`, hitung `duplicate_pattern`, log ETL run (`etl_runs`).

### 2.2 Training Lokal Isolation Forest
- Notebook utama: `ml/training/notebooks/deteksi_anomali_unsupervised.ipynb`.
- Fitur mengikuti `ml/training/config/features.yaml`.  
- Pipeline: scaling numerik, one-hot kategori, training `IsolationForest`.  
- Artefak:
  - `ml/artifacts/isolation_forest_iso_v1.pkl`
  - `ml/artifacts/scaler_iso_v1.pkl`
  - `ml/artifacts/feature_columns.json`
  - `ml/artifacts/model_meta.json` (versi, prepared_by, timestamp, catatan).
- Panduan detail: `ml/training/local_training_guide.md`.

### 2.3 Refresh Skor & Quality Check
- Setelah training, jalankan:
  ```bash
  python -m ml.pipelines.refresh_ml_scores --top-k 50
  python -m ml.pipelines.qc_summary
  ```
- Output:
  - Cache ML: `instance/data/claims_ml_scores.parquet` + tabel DuckDB `claims_ml_scores`.  
  - Log QC: `instance/logs/ml_scores_qc_<timestamp>.json`.  
  - Ringkasan agregat: `instance/logs/ml_scores_qc_summary.json`.  
- Script helper: `ops/scripts/refresh_ml_scores.sh`.  
- Runbook: `docs/ops/runbook_risk_scoring.md`.

### 2.4 API Risk Engine
- Service utama: `app/services/risk_scoring.py`  
  - Memuat klaim (via `DataLoader`), menggabungkan skor ML + rules (`short_stay`, `severity_mismatch`, `high_cost_full_paid`, *todo* `duplicate_pattern`).  
  - Menyediakan filter: `province`, `dx`, `severity`, `service_type`, `facility_class`, `start_date`, `end_date`, `min_risk_score`, `max_risk_score`, `min_ml_score`, pagination, `refresh_cache`.  
  - Response: `{"items": [...], "total": ..., "page": ..., "page_size": ..., "model_version": ..., "ruleset_version": ...}`.
- Endpoint `/claims/high-risk` (JWT protected) memanfaatkan service di atas. Swagger (`app/api/docs/spec.py`) telah diperbarui.

---

## 3. Komponen Agentic AI

### 3.1 Audit Copilot (LLM Komunikasi)
- Endpoint yang direncanakan: `GET /claims/{id}/summary`.  
- Fungsi:
  1. Mengambil klaim detail (`claims_normalized`, dx sekunder, peer stats, flags, skor).  
  2. Membentuk payload JSON menurut resep LLM (lihat `resource/docs_teknis/ml-llm-recipes.md`).  
  3. Memanggil LLM untuk membuat ringkasan audit (indikasi + pertanyaan tindak lanjut).  
  4. Cache hasil per `claim_id` & versi model/rules.

### 3.2 Feedback Loop (LLM Pembelajar)
- Auditor memberikan feedback melalui endpoint (misal `POST /claims/{id}/feedback`) untuk menyimpan `audit_outcome` (`decision`, `correction_ratio`, `notes`).  
- Data label disimpan untuk:
  - Tuning bobot rules (mis. severity mismatch) jika banyak false positive.  
  - Training model supervised (ketika label cukup) dengan metrik `PR-AUC`, `Precision@K`, dll.  
- Mendukung monitoring performa (prediksi vs feedback) di dashboard.

### 3.3 Validator Agent
- Membaca `ml_scores_qc_summary.json`.  
- Memeriksa apakah `amount_claimed_top_k_mean` >> populasi, proporsi LOS ≤ 1 meningkat, dsb.  
- Bila anomali, kirimkan alert ke channel ops (Slack/email).  
- Menyimpan status validasi untuk audit log.

### 3.4 Data Simulation Agent (LLM)
- Dokumen `docs/ops/data_simulation.md`.  
- Tujuan: generasi klaim sintetis tiap 10–30 detik untuk stress-test pipeline.  
- Skema:
  - LLM generator → JSON event (klaim fiktif).  
  - Channel event (file JSONL atau Kafka).  
  - Consumer → staging table `claims_live_stream` → scoring realtime.  
- Agent ini tidak terkait audit copilot; berfungsi sebagai alat testing.

---

## 4. Flow Harian & Skenario

1. **ETL**: `python pipelines/claims_normalized/build_claims_normalized.py`  
2. **Training (jika update)**: jalankan notebook lokal → simpan artefak.  
3. **Refresh Skor**: `python -m ml.pipelines.refresh_ml_scores --top-k 50` + `qc_summary`.  
4. **API Running**: `flask --app wsgi.py run` → endpoint `/claims/high-risk`.  
5. **Auditor Workflow**:  
   - Login (JWT).  
   - `/claims/high-risk` → klaim prioritas (filter/pagination).  
   - Klik klaim → (future) `/claims/{id}/summary` untuk ringkasan LLM.  
   - Catatan audit (feedback) dikirim ke backend.  
6. **Monitoring**:  
   - Baca `ml_scores_qc_summary.json` → dashboard/alert.  
   - Validator agent menandai pergeseran pola.  
7. **Simulasi Realtime (opsional)**: jalankan agent LLM → alirkan klaim ke staging untuk pengujian UI & pipeline live.

---

## 5. Perubahan Utama (Patch 1.1)

- Hapus `ml/training/colab_guidelines.md`; ganti dengan `ml/training/local_training_guide.md`.  
- Tambah `docs/ops/runbook_risk_scoring.md` (SLA, refresh, rollback).  
- Tambah `docs/ops/data_simulation.md` (LLM generator klaim).  
- Update `app/services/risk_scoring.py` dan `/claims/high-risk` agar caching ML + filter lanjutan berjalan.  
- Update README & checkpoint (C2/C3) sesuai perubahan.

---

## 6. Backlog & Aksi Lanjutan

### 6.1 ETL & Rules
- Hash + salt `patient_key`.  
- Hitung `duplicate_pattern` (kunjungan ≤3 hari) dan integrasikan ke rule scoring (bobot 0.6).  
- Log ETL run ke tabel `etl_runs`.

### 6.2 Reporting
- Implementasikan data nyata untuk `/reports/severity-mismatch` dan `/reports/duplicates`.  
- Perbaiki `app/services/analytics.py` untuk casemix/analytics real.

### 6.3 Metadata Ruleset/Model
- Simpan versi ruleset (`ruleset_versions`) dan model (`ml_model_versions`) di DuckDB atau config.  
- Automasi catatan saat refresh cache (timestamp, versi, parameter).

### 6.4 Operasional
- Hubungkan `ops/scripts/refresh_ml_scores.sh` ke cron/CI setelah ETL (mis. jam 02:00).  
- Bangun visualisasi dari `ml_scores_qc_summary.json` (heatmap, tren flag); buat dashboard (mis. Jupyter + Plotly atau BI tool).  
- Tambahkan notifikasi (Slack/email) bila validator mendeteksi anomali.  
- Koordinasikan filter tambahan (tanggal discharge, kelas RS) dengan tim UI; update API bila diperlukan.

### 6.5 LLM & Feedback
- Implementasikan endpoint ringkasan audit (`/claims/{id}/summary`), cacherequest, dan styling prompt.  
- Buat endpoint penyimpanan feedback auditor (`audit_outcome`).  
- Siapkan pipeline supervised (saat label tersedia) dan integrasikan ke risk engine.

---

## 7. Rujukan Cepat

- ETL: `pipelines/claims_normalized/`  
- Training: `ml/training/notebooks/deteksi_anomali_unsupervised.ipynb`  
- Artefak ML: `ml/artifacts/`  
- Refresh skor & QC: `python -m ml.pipelines.refresh_ml_scores`, `python -m ml.pipelines.qc_summary`  
- Risk API: `/claims/high-risk` (`app/services/risk_scoring.py`)  
- LLM Recipe: `resource/docs_teknis/ml-llm-recipes.md`  
- Data Simulation: `docs/ops/data_simulation.md`  
- Runbook Ops: `docs/ops/runbook_risk_scoring.md`

---

Dengan patch 1.1, backend Casemind AI kini memiliki pipeline end-to-end yang produktif: data masuk via ETL, dikonversi menjadi skor rules + ML, disajikan lewat API, disiapkan untuk ringkasan LLM, serta siap menerima feedback auditor. Simulasi klaim dan runbook operasional membantu memastikan sistem dapat diuji secara realtime dan dipantau dengan baik. Pekerjaan lanjutan pada daftar backlog akan membawa engine ke level operasional penuh (hashing, duplicate flag, reporting, supervised learning, dan integrasi agentic AI lengkap).
