# Risk Scoring Runbook

Terakhir diperbarui: 15 Nov 2025  
PIC: Rido Maulana

## SLA & Jadwal

| Komponen              | Jadwal                                                                         | Catatan                                                                                                                    |
| --------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| Refresh cache skor ML | Setelah ETL `claims_normalized` selesai (default setiap malam pukul 02:00 WIB) | Jalankan `python -m ml.pipelines.refresh_ml_scores --top-k 50` atau script `ops/scripts/refresh_ml_scores.sh` via cron/CI. |
| Regenerasi QC summary | Setelah refresh cache                                                          | Jalankan `python -m ml.pipelines.qc_summary`.                                                                              |

Jika refresh gagal, gunakan cache terakhir (Parquet + tabel DuckDB) sampai masalah teratasi.

## Proses Operasional

### Refresh Cache & QC

1. Pastikan ETL terbaru sudah selesai (`pipelines/claims_normalized/build_claims_normalized.py`).
2. Jalankan:
   ```bash
   source .venv/bin/activate
   python -m ml.pipelines.refresh_ml_scores --top-k 50
   python -m ml.pipelines.qc_summary --logs-dir instance/logs --output instance/logs/ml_scores_qc_summary.json
   deactivate
   ```
3. Verifikasi:
   - File `instance/data/claims_ml_scores.parquet` timestamp terbaru.
   - Tabel `claims_ml_scores` dalam `instance/analytics.duckdb` berisi jumlah baris yang sama.
   - Log QC baru di `instance/logs/ml_scores_qc_<timestamp>.json`.

### Rollback Cache

Jika refresh menghasilkan data tidak valid:

1. Hapus Parquet baru dan salin kembali versi sebelumnya (simpan backup minimal 1 hari).
2. Di DuckDB:
   ```sql
   -- gunakan backup tabel / rename
   DROP TABLE IF EXISTS claims_ml_scores;
   CREATE TABLE claims_ml_scores AS SELECT * FROM claims_ml_scores_backup;
   ```
3. Jalankan ulang `python -m ml.pipelines.qc_summary` untuk meng-update ringkasan.

### Endpoint `/claims/high-risk`

- Pastikan API menggunakan environment variable JWT & RULESET sesuai.
- Monitoring:
  - `meta.total` ≈ 1.176.438 (tanpa filter).
  - Respon sample: `GET /claims/high-risk?service_type=RITL&severity=sedang&page_size=5`.

## Alert & Monitoring

- Gunakan ringkasan dari `instance/logs/ml_scores_qc_summary.json` untuk memonitor perubahan:
  - Perbandingan `amount_claimed_top_k_mean` antar run.
  - Proporsi `los <= 1` di top-K.
  - Klaim top-K per provinsi / severity.
- Notifikasi manual: bila metrik jauh dari baseline, trigger investigasi dan pertimbangkan refresh ulang.

## Rujukan

- Script cron: `ops/scripts/refresh_ml_scores.sh`
- Dokumentasi API: `app/api/docs/spec.py`
- Checkpoint terkait: `docs/dev_checkpoint/checkpoint_3_risk_api_integration.md`
