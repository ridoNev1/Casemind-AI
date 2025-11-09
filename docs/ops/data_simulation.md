# Data Simulation via LLM Agent

Dokumen ini menjadi SOP singkat untuk mensimulasikan klaim baru secara berkala (setiap ±10 detik) menggunakan agen LLM sehingga data demo selalu terlihat “hidup”. Semua referensi ada di skrip `ops/simulation/run_simulator.py`.

---

## 1. Arsitektur & Tujuan

1. **Generator (LLM-first)**
   - Skrip CLI mengambil sampel 1 baris dari tabel `claims_normalized` di DuckDB → digunakan sebagai konteks prompt.
   - Agen LLM (default `gpt-4o-mini`) menghasilkan JSON klaim baru yang sudah menyertakan diagnosis, biaya, LOS, flags, dan narasi singkat.
   - Jika `SIM_FORCE_LLM=true` (default), simulasi akan gagal bila LLM tidak tersedia, sehingga memastikan seluruh data benar-benar generatif.
2. **Fallback Mutator**
   - Jika ingin mode offline, set `SIM_FORCE_LLM=false`. Skrip akan melakukan mutasi deterministik (biaya, LOS, flag) namun tetap menyuntikkan skor risiko tinggi untuk proporsi klaim fraud.
3. **Ingestion**
   - Payload langsung ditulis ke tabel `claims_live_stream` (skema salinan `claims_normalized`).
   - Setiap run dicatat di `instance/logs/simulation_runs.jsonl` sehingga mudah dilihat history-nya.

Dengan mode di atas kita dapat:

- Memperlihatkan feed klaim fraud baru di dashboard High-Risk tanpa menyentuh data asli.
- Mengatur rasio fraud vs normal melalui parameter tanpa menulis ulang kode.
- Menjalankan demo “auditor baru login → ada klaim baru muncul” hanya dengan menjalankan simulator selama beberapa menit.

---

## 2. Konfigurasi Environment

Tambahkan variabel berikut ke `.env` (sudah dicontohkan di `.env.example`):

| Key                    | Default                               | Keterangan                                                                                      |
| ---------------------- | ------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `DUCKDB_PATH`          | `/data/analytics.duckdb`              | Jalur database utama.                                                                           |
| `SIM_INTERVAL_SECONDS` | `10`                                  | Interval dasar antar klaim.                                                                     |
| `SIM_DURATION_SECONDS` | `300`                                 | Durasi default (detik).                                                                         |
| `SIM_MAX_CLAIMS`       | `120`                                 | Batas jumlah klaim per run.                                                                     |
| `SIM_INTERVAL_JITTER`  | `0.3`                                 | Variasi interval ±30%.                                                                          |
| `SIM_FRAUD_RATIO`      | `0.8`                                 | Peluang klaim hasil LLM bertipe fraud.                                                          |
| `SIM_FORCE_LLM`        | `true`                                | Jika true dan LLM gagal → skrip melempar error. Set ke `false` bila ingin mengizinkan fallback. |
| `SIM_LLM_MODEL`        | `gpt-4o-mini`                         | Model Responses API.                                                                            |
| `SIM_CLAIM_PREFIX`     | `SIM`                                 | Prefix ID (output mis. `SIM-AB12C3...`).                                                        |
| `SIM_LOG_PATH`         | `instance/logs/simulation_runs.jsonl` | Lokasi log run.                                                                                 |

Wajib juga menyuplai `OPENAI_API_KEY` (atau `OPEN_AI_API_KEY`). Tanpa itu, mode default akan berhenti dengan pesan “SIM_FORCE_LLM=true ...”.

---

## 3. Cara Menjalankan

### CLI Manual

```bash
source .venv/bin/activate
python -m ops.simulation.run_simulator \
  --duration 600 \
  --interval 8 \
  --max-claims 150 \
  --jitter 0.25 \
  --fraud-ratio 0.85
```

Output:

```
Simulation completed. Inserted 150 claims in 598.2s (DuckDB: /data/analytics.duckdb).
```

Setiap klaim otomatis masuk ke tabel `claims_live_stream` (skema identik dengan `claims_normalized`). Endpoint / job backend bisa membaca tabel ini kapan saja—tinggal tambahkan query DuckDB yang meng-union-kan `claims_live_stream` terhadap `claims_normalized` bila ingin menampilkannya di UI.

### Cron / Scheduler 10-detik

1. Buat cron job di Railway “Scheduled Tasks” atau pakai supervisor (mis. `watchman`) yang menjalankan perintah di atas setiap 30 menit.
2. Untuk interval sangat rapat (mis. 10 detik) gunakan parameter:
   ```
   SIM_INTERVAL_SECONDS=10
   SIM_INTERVAL_JITTER=0.15
   SIM_DURATION_SECONDS=3600  # jalankan satu jam penuh
   ```
3. Setelah run selesai _tidak perlu_ langsung refresh ML scores kecuali ingin klaim sintetis tersebut ikut di-cache `claims_ml_scores.parquet`. Untuk demo dashboard cukup membaca langsung dari DuckDB (sudah dilakukan backend). Jika suatu saat ingin pipeline scoring ulang, jalankan manual:
   ```
   python -m ml.pipelines.refresh_ml_scores --top-k 50
   ```
   Lakukan dari CLI/worker terpisah agar tidak membebani Gunicorn.

### Trigger Saat Login?

- Hindari otomatis menjalankan simulator setiap login karena bisa menumpuk ribuan data.
- Lebih aman menyediakan tombol admin “Inject 5 minutes of synthetic claims” yang memanggil skrip ini melalui job worker, atau jalankan cron pada jam tertentu saja.

---

## 4. Detail Implementasi

- **LLM Prompting**
  - Input: ringkasan klaim real (diagnosa, biaya, LOS, fasilitas).
  - Output: JSON yang berisi `dx_primary_*`, `severity_group`, `service_type`, `los`, `amount_claimed`, `amount_paid`, `flags`, `dx_secondary_codes`, dan narasi.
  - Skrip memberi tahu model apakah klaim harus “fraudulent/high-risk” atau “legitimate”.
  - Rasio fraud dikontrol lewat argumen CLI `--fraud-ratio` atau env `SIM_FRAUD_RATIO`. Default 0.8 → mayoritas klaim yang diproduksi terlihat berisiko.
- **Skor Risiko Otomatis**
  - Setelah JSON diterima, skrip menghitung `risk_score`, `rule_score`, `ml_score`, dan `ml_score_normalized` agar cocok dengan format API. Fraudulent claims otomatis diberi skor tinggi & flag relevan (`short_stay_high_cost`, `high_cost_full_paid`, dsb).
- **Claim ID**
  - Dibangkitkan dengan prefix `SIM` dan potongan UUID, contoh `SIM-7E2D4C8B9F10`. Hampir mustahil bentrok. Ubah prefix via `SIM_CLAIM_PREFIX` bila butuh environment berbeda.
- **Logging**
  - Setiap run menyimpan metadata: waktu mulai/selesai, jumlah klaim, jumlah fraud, target fraud ratio, model LLM yang dipakai, serta status `force_llm`. Gunakan log ini untuk audit atau debugging.
- **Beban Server**
  - Satu proses simulator + LLM memakan ±2–3 GB selama inference burst (tergantung model). Karena proses dijalankan dari CLI/worker lain, container Gunicorn tidak ikut melonjak.
  - Jangan jalankan lebih dari satu proses simultan agar tidak menghabiskan storage (tabel DuckDB bisa membengkak >5 GB). Monitor `/data/analytics.duckdb` secara berkala.

---

## 5. Data Hygiene & Pembersihan

- Gunakan query di DuckDB untuk menghapus klaim simulasi lama:
  ```sql
  DELETE FROM claims_live_stream WHERE generated_at < now() - INTERVAL '7 days';
  ```
- Kompres file log bila sudah terlalu besar (tar atau rotate).
- Jika storage hampir penuh, hapus file `claims_live_stream` via `VACUUM`/`DELETE` lalu `python -m ml.pipelines.refresh_ml_scores` sekali untuk rebuild cache bersih.

---

## 6. FAQ

**Apakah perlu refresh ML scores setiap kali simulasi?**  
Tidak. Endpoint `/claims/high-risk` membaca langsung dari DuckDB sehingga klaim baru otomatis ikut. Jalankan refresh hanya bila ingin memperbarui cache `claims_ml_scores.parquet` untuk analitik offline.

**Apakah klaim sintetis dijamin unik?**  
Ya, ID dibuat dari UUID, ditambah LLM juga dapat mengganti field lain (diagnosa/fasilitas) sehingga nyaris tidak ada duplikasi.

**Bisa generate data dinamis tanpa LLM?**  
Set `SIM_FORCE_LLM=false` bila ingin fallback mutator. Namun mode default sudah full LLM sehingga variasi klaim jauh lebih kaya dan menonjolkan kasus fraud.

**Apakah generator memberatkan server?**  
Prosesnya berdiri sendiri di CLI, jadi Gunicorn worker aman. Pastikan hanya menjalankan saat dibutuhkan dan batasi `SIM_MAX_CLAIMS` agar file DuckDB tidak membengkak.

---

Dengan panduan ini, tim ops dapat men-setup cron 10 detik atau job periodik lainnya tanpa mengubah kode backend utama, dan tim demo memiliki stok klaim fraud baru yang selalu terasa aktual.

`python -m ops.simulation.run_simulator --duration 120 --interval 5 --max-claims 8 --fraud-ratio 0.85`
