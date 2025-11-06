# Checkpoint 2 — ML Skeleton & Data Access

Tanggal: 31 Oct 2025  
PIC: Rido Maulana (user)

## Scope

- Menyusun struktur dasar ekosistem ML (training/inference/common).
- Membuat `DataLoader` berbagi pakai untuk ML dan API.
- Menambah pipeline baseline yang mengonsumsi `claims_normalized`.

## Artefak Baru

- `ml/common/data_access.py`: helper memuat data dari DuckDB/Parquet menggunakan konfigurasi ETL.
- `ml/training/config/features.yaml`: daftar fitur numerik/kategorikal awal.
- `ml/training/pipelines/baseline_training.py`: scaffold training; memuat data, pilih fitur, tampilkan head/descriptive stats.
- Struktur folder `ml/common`, `ml/training/{config,notebooks,pipelines}`, `ml/inference`.
- README root ditambah bagian **ML Skeleton**.
- `ml/inference/scorer.py`: contoh modul inference memuat artefak Isolation Forest dan menghasilkan `ml_score`.

## Cara Menggunakan

1. Pastikan ETL `claims_normalized` sudah dijalankan (tabel + Parquet tersedia).
2. Untuk eksplor cepat lokal, jalankan:
   ```bash
   python -m ml.training.pipelines.baseline_training
   ```
   (Pastikan tidak ada sesi DuckDB lain yang mengunci `instance/analytics.duckdb`.)
3. Training utama dilakukan secara lokal — lihat `ml/training/local_training_guide.md` untuk prosedur lengkap (load data, training Isolation Forest, ekspor artefak, refresh cache).

## Pembaruan — 14 Nov 2025

### Pencapaian
- Notebook `ml/training/notebooks/deteksi_anomali_unsupervised.ipynb` kini menjalankan alur penuh: memuat data via `DataLoader`, mengambil fitur sesuai `ml/training/config/features.yaml`, melakukan scaling numerik terpisah, encoding kategori, lalu melatih `IsolationForest` (200 trees, contamination 3%).
- Artefak baseline `iso_v1` tersimpan di `ml/artifacts/`:
  - `isolation_forest_iso_v1.pkl`
  - `scaler_iso_v1.pkl`
  - `feature_columns.json`
  - `model_meta.json` (sudah diisi `prepared_by` = Rido Maulana).
- Quality check: Top 3% klaim (berdasarkan `ml_score`) memiliki `amount_claimed` ±3× populasi dan `cost_zscore` ≈ 1.1; proporsi LOS ≤ 1 turun → sinyal klaim high-cost terangkat sesuai ekspektasi.
- `python -m ml.inference.scorer` berhasil memuat artefak dan menghasilkan `ml_score_normalized`, siap untuk dipakai backend.
- Service `app/services/risk_scoring.py` kini memakai `MLScorer` + ruleset untuk menghitung `risk_score`, membaca skor dari cache Parquet `instance/data/claims_ml_scores.parquet` (dapat di-refresh via query `refresh_cache=true`), dan mendukung pagination (`page`, `page_size`/`limit`).
- Endpoint `GET /claims/high-risk` mengekspose payload terstruktur: `data[]` + `meta` (`total`, `page`, `page_size`, `model_version`, `ruleset_version`, `filters`), mendukung filter lanjutan (`severity`, `service_type`, `min_risk_score`, `min_ml_score`) tanpa menghitung ulang skor.
- CLI `python -m ml.pipelines.refresh_ml_scores` tersedia untuk regenerasi cache (menulis ke Parquet + tabel DuckDB `claims_ml_scores`) sekaligus mencatat QC snapshot (`instance/logs/`).
- `requirements.txt` diperbarui dengan dependensi notebook/training (`matplotlib`, `seaborn`, `scikit-learn`, `joblib`).

> Lihat `docs/dev_checkpoint/todo.md` untuk backlog ML selanjutnya.

### Pembaruan — 6 Nov 2025
- Tambah modul schema validator (`ml/common/schema.py`) dan opsi `validate=True` pada `DataLoader.load_claims_normalized` untuk memastikan kolom wajib tersedia sebelum training/inference.
