# Data Simulation via LLM Agent

## Tujuan

- Menghasilkan klaim sintetis setiap 10–30 detik untuk meniru intake realtime.
- Menguji pipeline scoring dan agent orchestration tanpa memakai data PHI asli.
- Menyediakan data sandbox untuk demo UI dan integrasi.

## Skema Workflow

1. **Generator LLM**
   - Menggunakan prompt template versi klaim (ID, waktu admit/discharge, diagnosis, fasilitas, biaya).
   - Output JSON disesuaikan dengan distribusi statistik `claims_normalized` (rentang LOS, biaya rata-rata).
2. **Channel Output**
   - Publishing ke log file JSONL atau streaming (Redis, Kafka).
   - Interval 10–30 detik (jitter).
3. **Ingestion**
   - Skrip consumer memasukkan data ke tabel staging (mis. `claims_live_stream`).
   - Pipeline scoring dapat dijalankan near realtime untuk validasi.

## Contoh Payload

```json
{
  "claim_id": "SIM-2025-001",
  "admit_dt": "2025-11-15T08:12:00Z",
  "discharge_dt": "2025-11-16T11:15:00Z",
  "facility": {
    "province": "JAWA TIMUR",
    "class": "RS Kelas B",
    "ownership": "Pemkab"
  },
  "diagnosis": {
    "primary_code": "O63",
    "primary_label": "Prolonged labour",
    "secondary_codes": ["Z348", "O441"]
  },
  "procedure": {
    "code": "8631",
    "label": "Cesarean section"
  },
  "severity_group": "sedang",
  "service_type": "RITL",
  "amount_claimed": 4500000,
  "amount_paid": 3800000,
  "amount_gap": 700000,
  "generated_at": "2025-11-15T08:12:01Z"
}
```

## Implementasi Singkat

1. Notebook `simulate_claims_agent.ipynb` → memanggil LLM dengan prompt, menyimpan output ke JSONL/stream.
2. Flask/FastAPI service optional: endpoint `/simulate/claims` untuk menghasilkan klaim on-demand.
3. Consumer (Python script) membaca stream dan menulis ke DuckDB/Parquet khusus `claims_live_stream`.
4. Manfaatkan `refresh_ml_scores` untuk menguji scoring gabungan (klaim nyata + simulasi).

## Catatan

- Pastikan data sintetis tidak memuat informasi sensitif asli.
- Atur konfigurasi interval dan output path via environment variable.
- Pisahkan sumber data simulasi dari prod (schema atau database berbeda).
- Agent ini independen dari LLM audit copilot; tujuannya murni simulasi data realtime.
