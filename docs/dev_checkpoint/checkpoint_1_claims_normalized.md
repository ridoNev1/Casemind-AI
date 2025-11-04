# Checkpoint 1 — claims_normalized ETL

Tanggal: 31 Oct 2025  
PIC: Rido Maulana (user)

## Scope

- Menyiapkan kerangka ETL untuk membangun tabel `claims_normalized` sesuai blueprint pada `resource/docs_teknis/data-recipes.md` dan `resource/docs_teknis/ml-llm-recipes.md`.
- Menambahkan struktur direktori pipeline, konfigurasi, dan dokumentasi checkpoint.
- ETL telah dijalankan penuh dan kini menghasilkan tabel `claims_normalized`/`claims_scored` beserta export Parquet di `instance/data/`.

## Artefak Baru

- `pipelines/claims_normalized/README.md`: Dokumen deskripsi pipeline dan struktur file.
- `pipelines/claims_normalized/config.yaml`: Konfigurasi sumber data & output (DuckDB, Parquet, ruleset).
- `pipelines/claims_normalized/sql/staging.sql`: SQL untuk load data mentah ke staging DuckDB.
- `pipelines/claims_normalized/sql/transform.sql`: SQL transform yang menambahkan label fasilitas/wilayah, peer stats, lookup provinsi, dan membuat `claims_scored`.
- `pipelines/claims_normalized/build_claims_normalized.py`: Runner script untuk eksekusi ETL.
- `docs/dev_checkpoint/checkpoint_1_claims_normalized.md`: dokumen ini.

## Cara Menggunakan

1. Update `.env` atau `pipelines/claims_normalized/config.yaml` jika path data berubah.
2. Pastikan virtualenv aktif dan dependency `duckdb` tersedia.
3. Jalankan:
   ```bash
   python pipelines/claims_normalized/build_claims_normalized.py
   ```
   Output:
   - Tabel `claims_normalized` & `claims_scored` di `instance/analytics.duckdb`.
   - Parquet `instance/data/claims_normalized.parquet`.
4. Verifikasi di DuckDB (contoh):
   ```sql
   SELECT COUNT(*) FROM claims_normalized;
   SELECT province_name, COUNT(*) FROM claims_normalized GROUP BY 1;
   ```

## Next Steps

- Validasi hasil transform (label fasilitas/wilayah) dan tambahkan referensi ICD/metadata tambahan bila diperlukan – status: provinsi sudah dilengkapi lewat `province_lookup_stage`, perlu cek apakah perlu memasukkan nama fasilitas/ICD tambahan.
- Tambahkan hashing dengan salt untuk `patient_key`.
- Logging ETL run (`etl_runs` table) + metadata field `ruleset_version`.
- Integrasikan pipeline ini ke service risk scoring (gantikan data mock).
