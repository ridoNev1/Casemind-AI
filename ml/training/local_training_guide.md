# Panduan Training Lokal — Deteksi Anomali `claims_normalized`

Dokumen ini menjelaskan cara melatih model Isolation Forest secara lokal menggunakan
notebook `ml/training/notebooks/deteksi_anomali_unsupervised.ipynb`. Hasil training
dijadikan artefak inference untuk risk engine di backend.

## 1. Prasyarat

1. **Data ETL siap** – Jalankan pipeline `pipelines/claims_normalized/build_claims_normalized.py`
   sehingga DuckDB (`instance/analytics.duckdb`) dan Parquet (`instance/data/claims_normalized.parquet`)
   berisi tabel `claims_normalized`.
2. **Lingkungan virtual** – Aktifkan venv yang sudah berisi dependensi repo:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Notebook environment** – Jalankan Jupyter/VS Code/Colab lokal dan buka
   `ml/training/notebooks/deteksi_anomali_unsupervised.ipynb`.

## 2. Struktur Notebook

Notebook sudah dipaketkan dengan langkah berikut:

1. Memuat data via `DataLoader` langsung dari DuckDB
   (tidak perlu upload ke Colab).
2. Eksplorasi data: info, distribusi, korelasi, outlier (IQR), frekuensi severity.
3. Pre-processing:
   - Mengambil daftar fitur dari `ml/training/config/features.yaml`.
   - Menangani nilai hilang (`comorbidity_count`, `cost_zscore`).
   - Men-standardisasi fitur numerik dengan `StandardScaler` dan menyimpan urutan kolom.
   - One-hot encoding kategori baseline (`severity_group`, `facility_class`, `province_name`, `service_type`).
4. Training Isolation Forest (`n_estimators=200`, `contamination=0.03`, `random_state=42`).
5. Menyatukan skor ke DataFrame dan menghitung `ml_score_normalized`.
6. Quality check (Top 3% summary: biaya, cost_zscore, proporsi LOS ≤ 1).
7. Ekspor artefak ke `ml/artifacts/`:
   - `isolation_forest_iso_v2.pkl`
   - `scaler_iso_v2.pkl`
   - `feature_columns.json`
   - `model_meta.json`

## 3. Prosedur Training

1. Aktifkan venv dan jalankan notebook secara berurutan (pastikan koneksi ke DuckDB
   tidak dikunci oleh proses lain).
2. Setelah notebook selesai:
   - Isi field `prepared_by` dan metadata lain pada `model_meta.json`.
   - Pastikan artefak tersimpan di `ml/artifacts/`.
3. Jalankan refresh skor supaya backend membaca artefak baru:
   ```bash
   source .venv/bin/activate
   python -m ml.pipelines.refresh_ml_scores --top-k 50
   python -m ml.pipelines.qc_summary
   ```
   Hasilnya:
   - Cache ML (`instance/data/claims_ml_scores.parquet` + tabel DuckDB `claims_ml_scores`).
   - Log QC per run (`instance/logs/ml_scores_qc_<timestamp>.json`).
   - Ringkasan agregat (`instance/logs/ml_scores_qc_summary.json`).

## 4. Validasi & Dokumentasi

1. **Manual sanity check** – Buka QC log terbaru dan pastikan:
   - Top 3% memiliki biaya lebih tinggi dari populasi dan LOS ≤ 1 lebih dominan.
   - Distribusi provinsi/severity sesuai ekspektasi.
2. **Update checkpoint** – Catat run terbaru di
   `docs/dev_checkpoint/checkpoint_3_risk_api_integration.md` (tanggal training,
   parameter penting, link notebook).
3. **Tambahkan log** – Jika ada insight khusus (mis. fitur baru, alasan tuning),
   dokumentasikan di runbook atau checkpoint.

## 5. Langkah Lanjut Setelah Training

- Jalankan API lokal: `flask --app wsgi.py run`, lalu akses
  `GET /claims/high-risk` untuk memastikan skor dan artefak baru terbaca.
- Jika ingin melakukan tuning ulang, duplikasi notebook dengan versi berbeda
  (misal `deteksi_anomali_unsupervised_v2.ipynb`) dan ulangi prosedur di atas.
- Simpan artifact lama jika ingin rollback (taruh di folder versi atau gunakan
  branch git terpisah).

Dengan mengikuti panduan ini, proses training dapat dilakukan sepenuhnya di lokal
tanpa ketergantungan Google Colab, sementara backend risk engine tetap
menyinkronkan skor dan QC log secara konsisten.
