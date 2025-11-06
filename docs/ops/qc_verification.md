# QC Verification Playbook

Terakhir diperbarui: 6 Nov 2025  
PIC: Rido Maulana (user)

Panduan ini memberikan checklist ringkas untuk tim auditor/ops dalam memantau kualitas pipeline `claims_normalized` + skor ML. Jalankan prosedur ini setiap kali ETL & refresh skor selesai (default harian) dan lakukan sampling manual mingguan.

---

## A. Setelah Refresh Skor (Harian)

1. **Jalankan pipeline**  
   ```bash
   python pipelines/claims_normalized/build_claims_normalized.py --refresh-ml --refresh-top-k 50
   python -m ml.pipelines.qc_summary
   ```
   Ini memastikan log detail (`ml_scores_qc_<timestamp>.json`) dan ringkasan (`ml_scores_qc_summary.json`) diperbarui.

2. **Verifikasi metadata audit trail (ops / data)**  
   ```bash
   duckdb instance/analytics.duckdb "
     SELECT executed_at, rows_processed
     FROM etl_runs
     ORDER BY executed_at DESC
     LIMIT 1;
   "
   duckdb instance/analytics.duckdb "
     SELECT refreshed_at, top_k, json_extract(top_k_snapshot, '$.insights')
     FROM ml_model_versions
     ORDER BY refreshed_at DESC
     LIMIT 1;
   "
   ```
   Pastikan timestamp terbaru sesuai run yang barusan dijalankan, serta kolom `top_k_snapshot` terisi ringkasan insight Top‑K.

3. **Periksa status cepat (ops / FE)**  
   ```bash
   curl -H "Authorization: Bearer <token>" http://<host>/analytics/qc-status
   ```
   - `status: "ok"` → pipeline dalam ambang normal.  
   - `status: "alert"` → baca field `message`, `metrics`, `top_provinces`, `top_flags` untuk investigasi awal.  
   - `status: "no_data"` → ringkasan belum tersedia (cek apakah refresh sukses).

4. **Visualisasi (ops / data analyst)**  
   - Buka notebook `notebooks/qc_dashboard.ipynb` → jalankan seluruh sel untuk melihat heatmap provinsi, tren risk score & LOS ≤ 1, dan flag dominan.  
   - Simpan insight penting (misal top flag mendadak meningkat) pada catatan harian.

5. **Validasi ambang**  
   - Default ambang alert: `risk_score_top_k_mean ≥ 0.7`, `los_le_1_ratio_top_k ≥ 5%`.  
   - Jika ingin threshold berbeda (mis. pilot project), set env var `QC_ALERT_MIN_RISK_SCORE`, `QC_ALERT_MIN_LOS_RATIO`.

---

## B. Sampling Manual (Mingguan / Sesuai Jadwal)

1. **Ambil Top-K terbaru**  
   - Gunakan notebook QC atau query `instance/logs/ml_scores_qc_<timestamp>.json` untuk daftar klaim Top-K terakhir.

2. **Pilih sampel audit**  
   - Minimal 5–10 klaim dengan variasi provinsi/severity.  
   - Utamakan klaim dengan flag tertentu (mis. `short_stay_high_cost`, `duplicate_pattern`).

3. **Review data**  
   - Cross-check LOS, biaya klaim vs peer, flag rules, dan output copilot (`GET /claims/{id}/summary`).  
   - Jika ditemukan koreksi, simpan via `POST /claims/{id}/feedback` atau catatan audit internal.

4. **Catat temuan**  
   - Gunakan format sederhana (tanggal, claim_id, temuan, tindakan).  
   - Observasi penting (mis. banyak klaim Riau LOS tinggi) disampaikan ke tim data/rules untuk follow-up.

---

## C. Troubleshooting & Catatan

- **Ringkasan kosong** → Pastikan `python -m ml.pipelines.qc_summary` sudah dijalankan dan memiliki akses ke folder `instance/logs`.  
- **Alert berulang untuk provinsi tertentu** → Pertimbangkan tuning rules/threshold, atau lakukan investigasi ETL pada provinsi tersebut.  
- **Integrasi FE** → FE cukup memanggil `GET /analytics/qc-status` untuk menampilkan banner “OK/ALERT”.

Dokumen ini akan diperbarui ketika threshold berubah, indikator baru ditambahkan, atau workflow audit disesuaikan.
