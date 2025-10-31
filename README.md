# Casemind Claims Backend

Backend Flask + DuckDB untuk prototipe Casemind AI. Repo ini memuat API (register/login, claims, reports, analytics), pipeline ETL `claims_normalized`, serta materi pendukung (`resource/`) seperti data sample BPJS dan dokumentasi teknis.

## Prasyarat
- Python 3.11+ (direkomendasikan 3.13 sesuai venv saat ini)
- Virtualenv atau pyenv untuk isolasi
- DuckDB CLI opsional (memudahkan inspeksi data)
- Data sample sudah ada di `resource/private_bpjs_data` (tidak di-commit)

## Setup Cepat
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Siapkan file `.env` mengacu pada `.env.example`:
```bash
cp .env.example .env
# edit jika perlu (DATABASE_URL Postgres, SECRET_KEY, aturan JWT, dsb.)
```

Secara default, aplikasi memakai fallback SQLite (`sqlite:///instance/app.db`) bila `DATABASE_URL` tidak diset. Untuk koneksi Postgres, gunakan string `postgresql+psycopg://...`.

## Menjalankan Flask API
```bash
source .venv/bin/activate
flask --app wsgi.py run
```
Endpoint utama:
- `POST /auth/register` & `POST /auth/login`
- `GET /claims/high-risk`
- `GET /reports/severity-mismatch`, `GET /reports/duplicates`
- `GET /analytics/casemix`
- Swagger UI: `GET /docs/swagger`, OpenAPI JSON: `GET /docs/openapi.json`
- Healthcheck: `GET /health/ping`

Endpoint protected membutuhkan JWT (Authorization `Bearer <token>`).

## ETL `claims_normalized`
Pipeline berada di `pipelines/claims_normalized`. Struktur:
- `build_claims_normalized.py`: runner
- `config.yaml`: path sumber & output
- `sql/staging.sql`, `sql/transform.sql`: definisi staging + transform
- `dev_checkpoint/checkpoint_1_claims_normalized.md`: catatan progres

Eksekusi:
```bash
source .venv/bin/activate
python pipelines/claims_normalized/build_claims_normalized.py
```
Output:
- DuckDB file `instance/analytics.duckdb` berisi tabel `claims_normalized`, `claims_scored` dan tabel staging
- Parquet `instance/data/claims_normalized.parquet`

Contoh inspeksi:
```bash
duckdb instance/analytics.duckdb "SELECT COUNT(*) FROM claims_normalized;"
duckdb instance/analytics.duckdb "SELECT province_name, COUNT(*) FROM claims_normalized GROUP BY 1 LIMIT 10;"
```

## ML Skeleton
- `ml/common/data_access.py`: shared DataLoader (DuckDB/Parquet)
- `ml/training/config/features.yaml`: daftar fitur baseline
- `ml/training/pipelines/baseline_training.py`: scaffold training, saat ini memuat data & menampilkan sample/summary
- `ml/training/colab_guidelines.md`: panduan training model di Google Colab (Isolation Forest, artefak yang harus dihasilkan)

Jalankan contoh pipeline:
```bash
python -m ml.training.pipelines.baseline_training  # sample local inference (training utama dilakukan di Colab)
```

## Test
Contoh unit test tersedia (`tests/test_health.py`). Jalankan dengan (jika pytest terpasang):
```bash
pytest
```

## Roadmap / TODO
- Hash `patient_id_hash` dengan salt (saat ini masih hash mentah dari dataset)
- Ganti mock services (`app/services/*`) dengan query DuckDB/Postgres aktual
- Logging run ETL (`etl_runs`), jadwal otomatis
- Enrich label tambahan (nama fasilitas, ICD view) jika diperlukan oleh UI/ML

## Struktur Direktori Utama
```
app/                 # Flask app, API, services
pipelines/           # ETL scripts
instance/            # DuckDB dan output lokal (ignored di Git)
resource/            # Sampel data dan dokumentasi (raw data tidak di-commit)
tests/               # Tests
ml/                  # Placeholder modul training/inference
dev_checkpoint/      # Catatan progress
```

## Catatan
- `resource/private_bpjs_data/raw_cleaned` dikecualikan dari Git (lihat `.gitignore`).
- `instance/.gitignore` memblok file sensitif (`config.py`, `*.db`, `*.parquet`).
- JWT expiry default 3.600 detik (konfigurasi via `.env`).
