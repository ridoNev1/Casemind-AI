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

## Pembaruan — 15 Nov 2025

- `transform.sql` kini melakukan hashing + salt untuk `patient_key`/`family_key` menggunakan konfigurasi `hashing.*`.
- Flag `duplicate_pattern` (≤3 hari, DX & prosedur identik) dihitung langsung di ETL dan diteruskan ke `claims_scored`.
- `config.yaml` diperbarui untuk menyimpan salt hashing sehingga dapat dirotasi via konfigurasi.
- Dokumentasi pipeline (`README.md`) diperbarui; pipeline juga menambahkan kolom deskriptif diagnosis (`dx_primary_label`, `dx_primary_group`, `dx_secondary_labels`) serta agregasi nama fasilitas per kabupaten/provinsi (`region_facility_names*`) sehingga API menampilkan label yang informatif. Backlog lain lihat `docs/dev_checkpoint/todo.md`.
