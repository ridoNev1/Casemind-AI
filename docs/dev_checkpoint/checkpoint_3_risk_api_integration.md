# Checkpoint 3 — Risk Scoring API Integration

Tanggal: 15 Nov 2025  
PIC: Rido Maulana (user)

## Scope

- Migrasi API `/claims/high-risk` dari payload mock menjadi hasil scoring nyata (rules + ML).
- Menyiapkan cache skor ML supaya endpoint responsif tanpa menghitung ulang ±1.1 juta klaim.
- Mendukung filter lanjutan dan pagination untuk kebutuhan UI audit.
- Menyediakan mekanisme CLI untuk regenerasi skor + logging QC serta runbook operasional.

## Artefak & Perubahan Utama

- **Service** `app/services/risk_scoring.py`
  - Memuat skor dari cache (`instance/data/claims_ml_scores.parquet` + tabel DuckDB `claims_ml_scores`), fallback ke scoring realtime jika perlu.
  - Menghitung flag rules (`short_stay_high_cost`, `severity_mismatch`, `duplicate_pattern`, `high_cost_full_paid`) dan final `risk_score = max(rule_score, ml_score_normalized)`.
  - Menerapkan filter lanjutan (`severity`, `service_type`, `facility_class`, `start_date`, `end_date`, `min_risk_score`, `max_risk_score`, `min_ml_score`) dan pagination (`page`, `page_size`).
  - Menulis log QC di `instance/logs/ml_scores_qc_*.json` setiap cache di-refresh.
  - Respons kini menyertakan `facility_id`, `facility_name`, dan `facility_match_quality` (`exact`, `regional`, `unmatched`); filter tambahan `discharge_start`/`discharge_end` tersedia untuk menyaring tanggal pulang.
- **ETL** `pipelines/claims_normalized/transform.sql`
  - Join master RS menghasilkan mapping `facility_id` satu-ke-satu (prioritas kecocokan class/type/ownership) sekaligus tetap menyimpan agregasi regional untuk fallback.
  - Kolom `dx_primary_label` diisi ulang bila kosong menggunakan referensi ICD-10 CSV internal.

- **API Endpoint** `GET /claims/high-risk`
  - Sekarang mengembalikan struktur `{"data": [...], "meta": {...}}` dengan metadata (`total`, `page`, `page_size`, `model_version`, `ruleset_version`, `filters`).
  - Parameter query baru terdokumentasi: `page`, `page_size`/`limit`, `severity`, `service_type`, `facility_class`, `start_date`, `end_date`, `discharge_start`, `discharge_end`, `min_risk_score`, `max_risk_score`, `min_ml_score`, `refresh_cache`.
  - OpenAPI (`app/api/docs/spec.py`) diperbarui untuk mencerminkan skema terbaru + contoh filter yang valid.
- **API Endpoint** `GET /claims/{id}/summary` & `POST /claims/{id}/feedback`
  - Copilot summary menampilkan 6 bagian ringkasan + pertanyaan tindak lanjut berbasis flag/risk.
  - Endpoint feedback menyimpan keputusan auditor (`approved|partial|rejected`) beserta `correction_ratio` dan catatan.
  - Schema OpenAPI + Swagger sudah memuat contoh payload dan response.
- **Analytics & Reports**
  - `app/services/analytics.py` dan `app/api/analytics/routes.py` kini mengambil casemix provinsi langsung dari DuckDB (`claims_scored`).
  - `app/services/reports.py` / `/reports/severity-mismatch` & `/reports/duplicates` menggunakan resep SQL nyata (z-score > P90, window ≤3 hari).
  - Endpoint baru `/reports/tariff-insight` menampilkan agregasi gap tarif per fasilitas + casemix dengan filter province/facility/severity.
- **Agentic Copilot**
  - Service `app/services/audit_copilot.py` mempersiapkan summary deterministik; jika `OPEN_AI_API_KEY` tersedia akan memanggil OpenAI (`gpt-4o-mini`, cache di `instance/cache/copilot/`) untuk menghasilkan ringkasan generatif tambahan dengan prompt versi v1.
  - Tabel baru `audit_outcomes` (`app/models/audit_outcome.py`) menyimpan feedback auditor yang dikaitkan ke user dan klaim.

- **DataLoader Enhancements** (`ml/common/data_access.py`)
  - Mendukung filter aman ketika membaca `claims_normalized`.
  - Menyediakan helper untuk menulis DataFrame ke DuckDB (replace/append) dan membaca tabel cache.

- **Aritfak ML** (`ml/inference/scorer.py`)
  - Menambah `score_dataframe` sehingga artefak Isolation Forest dapat dipanggil ulang pada subset data apa pun.

- **CLI Refresh** `python -m ml.pipelines.refresh_ml_scores`
  - Menjalankan scoring penuh, menyimpan ke Parquet + tabel `claims_ml_scores`, dan menulis QC snapshot.
  - Metadata refresh otomatis masuk ke tabel `ml_model_versions` (timestamp, ringkasan QC, Top-K insight via kolom `top_k_snapshot`).
- **Metadata & Audit Trail**
  - Modul utilitas `ml.common.metadata` memastikan tabel `ruleset_versions`, `etl_runs`, dan `ml_model_versions` tersedia di DuckDB.
  - ETL `build_claims_normalized.py` mencatat jumlah baris + ruleset version ke `etl_runs`.
  - Refresh ML mencatat versi model, rows scored, metrik Top-K, serta snapshot insight (top provinsi/flags) ke metadata table.
- **CLI QC Summary** `python -m ml.pipelines.qc_summary`
  - Menghasilkan ringkasan agregat dari log QC (`instance/logs/ml_scores_qc_summary.json`).
- **Script scheduler** `ops/scripts/refresh_ml_scores.sh`
  - Helper untuk cron/CI menjalankan refresh otomatis (mengaktifkan venv + menjalankan script refresh).
- **Runbook** `docs/ops/runbook_risk_scoring.md`
  - Menjelaskan SLA, langkah refresh, rollback, dan monitoring.

## Cara Menggunakan

1. **Refresh skor** (setelah ETL):
   ```bash
   source .venv/bin/activate
   python -m ml.pipelines.refresh_ml_scores --top-k 50
   ```
   Output: cache Parquet + DuckDB diperbarui dan file QC baru dibuat.

2. **Menjalankan API**:
   ```bash
   flask --app wsgi.py run
   ```
   Endpoint: `GET /claims/high-risk?service_type=RITL&severity=sedang&page=1&page_size=50`
   (jangan lupa Authorization Bearer token).

3. **Contoh filter populer**:
   - `?service_type=RITL&severity=sedang` → banyak data tersedia.
   - `?facility_class=RS%20Kelas%20C&start_date=2022-11-01&end_date=2022-11-15` → filter lanjutan.
   - `?min_risk_score=0.9` → klaim dengan risiko tinggi saja.
   - `?refresh_cache=true` → memaksa regenerasi cache (gunakan hemat).

## Quality Check / Monitoring

- QC snapshot (`instance/logs/ml_scores_qc_*.json`) menyimpan:
  - Statistik ringkas (mean amount claimed / cost_zscore overall vs top-K).
  - Detail klaim Top-K untuk audit manual.
- Gunakan log ini untuk memonitor drift atau perbandingan antar-run.

> Catatan backlog lanjutan dipusatkan di `docs/dev_checkpoint/todo.md`.

### Pembaruan — 7 Nov 2025

- **Kolom finansial baru (FKL47/48) sudah aktif end-to-end**: ETL `build_claims_normalized.py` dijalankan ulang, sehingga `amount_claimed/amount_paid/gap` di DuckDB + Parquet mengikuti angka rupiah resmi.
- **Artefak ML iso_v2** kini menjadi sumber tunggal: setelah retraining notebook, `python -m ml.pipelines.refresh_ml_scores --top-k 50` menulis ulang tabel `claims_ml_scores` (verifikasi DuckDB menunjukkan seluruh 1.176.438 baris memakai `model_version='iso_v2'`).
- **Smoke test API** — `GET /claims/high-risk?service_type=RITL&severity=berat&facility_class=RS%20Kelas%20C&start_date=2022-11-01&end_date=2022-11-30&discharge_start=2022-11-05&discharge_end=2022-11-15&page_size=5` mengembalikan payload di mana `meta.model_version` dan setiap item `model_version` = `iso_v2`, serta nilai klaim sudah sesuai rupiah.
- **Audit Copilot** — `GET /claims/18591122V003624/summary` kini melaporkan `ml_score_normalized≈0.71` + `model_version=iso_v2`, sementara blok LLM mencatat ringkasan generatif baru (`cached=false`, provider OpenAI `gpt-4o-mini`). Respons ini dicatat sebagai referensi regresi manual untuk memastikan cache LLM dibersihkan setelah data berubah.
- **Chat UI Rencana** — FE akan memanfaatkan summary tersebut sebagai header ruang chat; history percakapan disediakan via `GET/POST /claims/{id}/chat` (persist di Postgres) sehingga agent `langchain-openai` dapat mempertahankan konteks. Detail interaksi list → chat → feedback terdokumentasi di `docs/dev_checkpoint/chat_copilot_workflow.md`.
- **Feedback Utilization Plan** — dataset monitoring + outline eksperimen supervised (saat label cukup) terdokumentasi di `docs/dev_checkpoint/feedback_utilization_plan.md`; ini jadi referensi siklus pembelajaran berikutnya.

### Pembaruan — 6 Nov 2025
- Notebook `notebooks/qc_dashboard.ipynb` menyediakan visualisasi heatmap Top-K provinsi, tren risk score & LOS ≤ 1, serta contoh logika alert berbasis `ml_scores_qc_summary.json`.
- Endpoint analitik baru `/analytics/qc-status` mengembalikan status QC (OK/alert) beserta metrik & ambang agar FE/ops dapat menampilkan banner peringatan.
