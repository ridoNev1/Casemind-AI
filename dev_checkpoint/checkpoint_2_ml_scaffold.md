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
3. Training utama dilakukan di Google Colab — lihat `ml/training/colab_guidelines.md` untuk prosedur lengkap (upload data, training Isolation Forest, export artefak, integrasi).

## Next Steps

- Tambahkan preprocessing & training model (rules + unsupervised) di pipeline.
- Simpan artefak ke `ml/artifacts/` beserta metadata (`model_meta.json`).
- Integrasikan DataLoader ke service API untuk menggantikan mock risk scoring.
- Definisikan feature schema/validation serta hashing `patient_key`.
