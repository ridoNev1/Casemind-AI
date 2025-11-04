# Claims Normalized ETL

Tujuan ETL ini adalah membangun tabel `claims_normalized` sebagai sumber tunggal untuk modul rule-based, analitik, dan ML. Pipeline akan:

1. `Stage` data mentah dari `resource/private_bpjs_data` (FKRTL, diagnosa sekunder, non-kap, kepesertaan).
2. `Enrich` dengan referensi publik dari `resource/public_data_resources` (ICD-10/9, master faskes/wilayah).
3. `Feature` untuk menghitung metrik penting seperti LOS, peer stats (`peer_mean`, `peer_p90`, `peer_std`), `cost_zscore`, flag dasar (LOS pendek, severity mismatch).
4. `Persist` hasil akhir ke file DuckDB (`instance/analytics.duckdb`) dan Parquet untuk konsumsi ML.

## Struktur Folder

```
pipelines/
  claims_normalized/
    README.md
    staging.sql          # definisi tabel staging + load
    transform.sql        # langkah join dan feature engineering
    build_claims_normalized.py  # eksekusi pipeline
    config.yaml          # parameter ETL (paths, salt, ruleset)
ml/
  training/              # notebook / script training
  inference/             # helper inference
  artifacts/             # model serialised
configs/
  etl.yaml (opsional)    # bisa simpan configuration global
/docs/dev_checkpoint/
  checkpoint_1_claims_normalized.md
```

## Langkah Eksekusi (draft)

1. Jalankan `python pipelines/claims_normalized/build_claims_normalized.py` (sementara manual, ke depan bisa dijadwalkan).
2. Script memuat konfigurasi, mengeksekusi `staging.sql` untuk membuat tabel staging di DuckDB.
3. `transform.sql` membentuk `claims_normalized`, menambahkan label fasilitas/wilayah/severity serta peer stats (termasuk lookup provinsi bawaan), lalu menulis ke Parquet di `instance/data/`.
4. Logging hasil (jumlah baris, timestamp, ruleset version) ke tabel `etl_runs`.

## Kebutuhan Data

- Private: `resource/private_bpjs_data` (FKRTL, Non-Kap, Diagnosa sekunder, Kepesertaan).
- Public: `resource/public_data_resources` (ICD-10/9, Master RS, Master Wilayah).

## Dependency Teknis

- Python 3.10+, DuckDB (via `duckdb` package), Pandas (jika perlu). Sudah ditambahkan `duckdb>=0.9` di `requirements.txt`.

Dokumen ini akan diperbarui setelah pipeline selesai diimplementasikan (mis. penambahan join ICD, hashing `patient_key`, logging ETL runs).
