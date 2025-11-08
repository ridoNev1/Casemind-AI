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
  2. **Transform**: hash + salt `patient_key`/`family_key`, menghitung LOS, amount gap, `peer_key`, `peer_mean/p90/std`, `cost_zscore`, serta flag `duplicate_pattern`. Menambah label fasilitas, severity, service type.  
  3. **Output**: menulis ke DuckDB (`instance/analytics.duckdb`) dan Parquet (`instance/data/claims_normalized.parquet`).
- **Status metadata**: pencatatan `etl_runs`, `ruleset_versions`, dan `ml_model_versions` sudah otomatis via helper `ml/common/metadata.py`.

### 2.2 Training Lokal Isolation Forest
- Notebook utama: `ml/training/notebooks/deteksi_anomali_unsupervised.ipynb`.
- Fitur mengikuti `ml/training/config/features.yaml`.  
- Pipeline: scaling numerik, one-hot kategori, training `IsolationForest`.  
- Artefak:
  - `ml/artifacts/isolation_forest_iso_v2.pkl`
  - `ml/artifacts/scaler_iso_v2.pkl`
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
  - Memuat klaim (via `DataLoader`), menggabungkan skor ML + rules (`short_stay`, `severity_mismatch`, `duplicate_pattern`, `high_cost_full_paid`).  
  - Menyediakan filter: `province`, `dx`, `severity`, `service_type`, `facility_class`, `start_date`, `end_date`, `min_risk_score`, `max_risk_score`, `min_ml_score`, pagination, `refresh_cache`.  
  - Response: `{"items": [...], "total": ..., "page": ..., "page_size": ..., "model_version": ..., "ruleset_version": ...}`.
- Endpoint `/claims/high-risk` (JWT protected), laporan DuckDB riil (`/reports/severity-mismatch`, `/reports/duplicates`), agregasi `/analytics/casemix`, serta copilot/feedback (`/claims/{id}/summary`, `/claims/{id}/feedback`). Swagger (`app/api/docs/spec.py`) telah diperbarui.

---

## 3. Komponen Agentic AI

### 3.1 Audit Copilot (LLM Komunikasi)
- Endpoint `GET /claims/{id}/summary` menyusun ringkasan audit deterministik (6 bagian + follow-up question) berdasarkan resep di `resource/docs_teknis/ml-llm-recipes.md`.  
- Payload memuat identitas klaim, ringkasan biaya, peer stats, alasan flag, risk highlight, dan daftar pertanyaan tindak lanjut.  
- Default-nya menampilkan template deterministik; jika `OPEN_AI_API_KEY` tersedia maka service otomatis memanggil OpenAI `gpt-4o-mini` (melalui `langchain-openai`) dan menyimpan cache ringkasan generatif di `instance/cache/copilot/`.
- FE akan menyajikan ringkasan ini sebagai **header chat room** sebelum percakapan agentic dimulai. Pesan chat dipersist di Postgres (`GET/POST /claims/{id}/chat`) agar bot memiliki memori lintas sesi. Desain lengkap tercatat di `docs/dev_checkpoint/chat_copilot_workflow.md`.

### 3.2 Feedback Loop (LLM Pembelajar)
- Auditor memberikan feedback melalui `POST /claims/{id}/feedback` yang menyimpan `audit_outcomes` (`decision`, `correction_ratio`, `notes`, reviewer).  
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
5. **Auditor Workflow (Chat UI)**:  
   - Login (JWT) lalu buka daftar `/claims/high-risk`.  
   - Pilih klaim → FE membuka chat room khusus claim_id dan memanggil `/claims/{id}/summary` untuk header + `GET /claims/{id}/chat` untuk history.  
   - Auditor berdialog dengan bot (LLM) di pane chat: pertanyaan lanjutan diterjemahkan menjadi call analytics/reports relevan via agent LangChain.  
   - Setiap bubble dikirim ke backend (`POST /claims/{id}/chat`) agar percakapan tersimpan.  
   - Kirim keputusan via panel feedback di chat (memanggil `POST /claims/{id}/feedback`); entri feedback ditampilkan kembali ke thread.
6. **Monitoring**:  
   - Baca `ml_scores_qc_summary.json` → dashboard/alert.  
   - Validator agent menandai pergeseran pola.  
7. **Simulasi Realtime (opsional)**: jalankan agent LLM → alirkan klaim ke staging untuk pengujian UI & pipeline live.

---

## 5. Perubahan Utama (Patch 1.1)

- Hash + salt `patient_key` + `family_key` di ETL dan tambah flag `duplicate_pattern` dengan bobot rules 0.6.  
- Ganti mock analytics (`/reports/*`, `/analytics/casemix`) dengan query DuckDB riil.  
- Tambah copilot summary + feedback endpoint (`GET /claims/{id}/summary`, `POST /claims/{id}/feedback`) dan model `audit_outcomes`.  
- Script ETL kini dapat otomatis memicu refresh skor ML (`--refresh-ml` / config `post_refresh_ml`), mempermudah jadwal cron/CI.  
- Endpoint baru `/analytics/qc-status` mengekspose status QC + ambang alert untuk konsumsi FE/ops.  
- Tambah playbook verifikasi periodik (`docs/ops/qc_verification.md`) untuk sampling manual & interpretasi QC summary.
- ETL memperkaya label diagnosis (`dx_primary_label`, `dx_primary_group`, `dx_secondary_labels`) agar siap tampil di API/FE tanpa lookup tambahan.
- Join master rumah sakit kini menghasilkan `facility_id`, `facility_name`, dan status kecocokan (`facility_match_quality` = exact/regional/unmatched) per klaim; agregasi regional tetap dipertahankan sebagai fallback.
- Laporan tarif baru `/reports/tariff-insight` menyajikan gap klaim vs pembayaran per fasilitas + casemix dengan filter province/facility/severity/service_type/dx_group.
- Copilot summary memanfaatkan OpenAI (`gpt-4o-mini`, via `OPEN_AI_API_KEY`) dengan caching per klaim (`instance/cache/copilot/`); respon tetap menyediakan fallback deterministik bila kredensial belum ada.
- Hapus `ml/training/colab_guidelines.md`; ganti dengan `ml/training/local_training_guide.md`.  
- Tambah `docs/ops/runbook_risk_scoring.md` (SLA, refresh, rollback) dan `docs/ops/data_simulation.md` (LLM generator klaim).  
- Update README & checkpoint (C2/C3) sesuai perubahan.

---

## 6. Backlog & Aksi Lanjutan

### 6.1 ETL & Rules
- ✅ Logging ETL run (`etl_runs`) + penyimpanan metadata ruleset/Top‑K kini otomatis saat pipeline dijalankan (`ml/common/metadata.py`).  
- Evaluasi bobot rules setelah ada feedback auditor (tuning berkala).

### 6.2 Reporting
- Kembangkan dashboard (heatmap provinsi, tren flag) berbasis `ml_scores_qc_summary.json`/Parquet.

### 6.3 Metadata Ruleset/Model
- ✅ Versi ruleset (`ruleset_versions`) dan model (`ml_model_versions`) tersimpan di DuckDB (termasuk snapshot Top‑K melalui kolom `top_k_snapshot`).  
- ✅ Automasi catatan saat refresh cache (timestamp, versi, parameter) aktif melalui script `build_claims_normalized.py` + `refresh_ml_scores.py`.

### 6.4 Operasional
- Hubungkan `ops/scripts/refresh_ml_scores.sh` ke cron/CI setelah ETL (mis. jam 02:00).  
- Tambahkan notifikasi (Slack/email) bila validator mendeteksi anomali.  
- Koordinasikan filter tambahan (tanggal discharge, kelas RS) dengan tim UI; update API bila diperlukan.

### 6.5 LLM & Feedback
- ✅ Integrasi OpenAI + caching respon selesai; fallback template deterministik tetap tersedia jika kredensial kosong.  
- TODO: dokumentasikan mekanisme invalidasi cache / bump prompt version dan gunakan feedback auditor untuk evaluasi berkala + eksperimen supervised (ketika label cukup) lalu integrasikan ke risk engine (lihat `docs/dev_checkpoint/feedback_utilization_plan.md`).

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

Dengan patch 1.1, backend Casemind AI kini memiliki pipeline end-to-end yang produktif: data masuk via ETL, dikonversi menjadi skor rules + ML, disajikan lewat API, disiapkan untuk ringkasan copilot, serta siap menerima feedback auditor. Simulasi klaim dan runbook operasional membantu memastikan sistem dapat diuji secara realtime dan dipantau dengan baik. Fokus lanjutan berada pada pencatatan metadata, dashboard/validator otomatis, serta integrasi LLM generatif dan supervised learning berbasis feedback.
