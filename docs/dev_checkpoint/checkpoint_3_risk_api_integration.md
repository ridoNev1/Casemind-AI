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
  - Menghitung flag rules (`short_stay_high_cost`, `severity_mismatch`, `high_cost_full_paid`) dan final `risk_score = max(rule_score, ml_score_normalized)`.
  - Menerapkan filter lanjutan (`severity`, `service_type`, `facility_class`, `start_date`, `end_date`, `min_risk_score`, `max_risk_score`, `min_ml_score`) dan pagination (`page`, `page_size`).
  - Menulis log QC di `instance/logs/ml_scores_qc_*.json` setiap cache di-refresh.

- **API Endpoint** `GET /claims/high-risk`
  - Sekarang mengembalikan struktur `{"data": [...], "meta": {...}}` dengan metadata (`total`, `page`, `page_size`, `model_version`, `ruleset_version`, `filters`).
  - Parameter query baru terdokumentasi: `page`, `page_size`/`limit`, `severity`, `service_type`, `min_risk_score`, `max_risk_score`, `min_ml_score`, `refresh_cache`.
  - OpenAPI (`app/api/docs/spec.py`) diperbarui untuk mencerminkan skema terbaru + contoh filter yang valid.

- **DataLoader Enhancements** (`ml/common/data_access.py`)
  - Mendukung filter aman ketika membaca `claims_normalized`.
  - Menyediakan helper untuk menulis DataFrame ke DuckDB (replace/append) dan membaca tabel cache.

- **Aritfak ML** (`ml/inference/scorer.py`)
  - Menambah `score_dataframe` sehingga artefak Isolation Forest dapat dipanggil ulang pada subset data apa pun.

- **CLI Refresh** `python -m ml.pipelines.refresh_ml_scores`
  - Menjalankan scoring penuh, menyimpan ke Parquet + tabel `claims_ml_scores`, dan menulis QC snapshot.
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

## Next Steps

1. **ETL & Rules**
   - Tambahkan hashing + salt `patient_key` di `claims_normalized` untuk memenuhi pedoman anonymisasi.
   - Hitung flag `duplicate_pattern` (kunjungan ≤3 hari; diagnosis/procedure sama) dan integrasikan ke `claims_scored` serta `risk_scoring.py` dengan bobot 0.6.
2. **Reporting**
   - Implementasikan query DuckDB agar service `/reports/severity-mismatch` dan `/reports/duplicates` tidak lagi dummy.
3. **Ruleset & Metadata**
   - Siapkan storage versi ruleset/model (mis. tabel `ruleset_versions` di DuckDB) untuk mencatat parameter RULESET_v1 & riwayat perubahan.
4. **Operasional & Monitoring**
   - Integrasikan cron/CI agar `ops/scripts/refresh_ml_scores.sh` berjalan otomatis setelah ETL.
   - Bangun visualisasi/alert berbasis `ml_scores_qc_summary.json` (heatmap provinsi, proporsi flags) dan lengkapi dashboard agar auditor dapat memantau tren tanpa skrip manual.
   - Sinkronkan kebutuhan filter tambahan (mis. tanggal discharge, klasifikasi fasilitas) dengan tim UI dan update API bila diperlukan.
