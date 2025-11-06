# Casemind AI — ML & LLM Recipes (Acuan Singkat)

## 0) Prasyarat Data
Gunakan satu tabel kerja: **`claims_normalized`** (1 baris = 1 episode klaim).  
Kolom minimum:
- **ID**: `claim_id`, `facility_id` (ops), `patient_key` (hash+salt)
- **Episode**: `admit_dt`, `discharge_dt`, `LOS`
- **Klinik**: `dx_primary_code`, `severity_group`, `service_type` (RITL/RJTL/IGD/NonKap)
- **Faskes/Wilayah**: `facility_class`, `ownership`, `province`
- **Finansial**: `amount_claimed`, `amount_paid`, `amount_gap`
- **Komorbid**: `comorbidity_count`
- **Peer stats** (hasil agregasi): `peer_mean`, `peer_p90`, `peer_std`, `cost_zscore`

> `cost_zscore = (amount_claimed - peer_mean) / peer_std`  
> Peer group = `(dx_primary_code, severity_group, facility_class, province)`

---

## 1) Unsupervised + Rules (MVP)

### 1.1 Flags (aturan deterministik)
- `short_stay_high_cost` → `LOS ≤ 1` **AND** `amount_claimed > peer_p90`
- `severity_mismatch` → `severity_group = 'ringan'` **AND** `amount_claimed > peer_p90`
- `duplicate_pattern` → pasien sama (hash), dx/procedure sama, jarak ≤3 hari
- `high_cost_full_paid` → `amount_paid/amount_claimed ≥ 0.95` **AND** `amount_claimed > peer_p90`

### 1.2 Skor Anomali (opsional)
Fitur numerik: `LOS, amount_claimed, amount_paid, amount_gap, cost_zscore, comorbidity_count`.  
Model ringan (contoh): Isolation-style / z-score gabungan.

### 1.3 Risk Score (gabungan)
```
rule_score = max(
  0.8 * short_stay_high_cost,
  0.7 * severity_mismatch,
  0.6 * duplicate_pattern,
  0.5 * high_cost_full_paid
)
risk_score = max(rule_score, normalized_anomaly_score)   # jika pakai anomaly
```
**Target kapasitas audit**: ambil **Top 3–5%** tertinggi.

### 1.4 Output API (read-only)
- `GET /claims/high-risk?province=...&dx=...` → `[ {claim_id, risk_score, flags[], peer_p90, cost_zscore, LOS, amount_claimed, amount_paid} ]`
- `GET /reports/severity-mismatch`
- `GET /reports/duplicates?days=3`

### 1.5 Validasi Harian (tanpa label)
- Median biaya **Top-5%** vs populasi (harus jauh lebih tinggi).
- Proporsi `LOS ≤ 1` di Top-N (harus meningkat).
- Sampling 20 kasus untuk review manual (face validity).

---

## 2) Menyiapkan Jalan ke Supervised (tanpa dipakai dulu)

### 2.1 Skema Label
Tabel: **`audit_outcome`**
- `claim_id` (FK), `decision` (`approved|partial|rejected`), `correction_ratio` (0–1), `notes` (ops), `review_dt`  
**Definisi label ke depan (saat ada data):**
- `label=1` jika `rejected` **atau** `correction_ratio ≥ 0.30`
- `label=0` jika `approved` **atau** `correction_ratio ≤ 0.10`
- sisanya `NULL` (tidak dipakai training)

### 2.2 Metrik nanti (saat supervised)
- **PR-AUC**, **Precision@K** (K = kapasitas audit), **Lift@K**
- Calibration check (reliability curve)

---

## 3) Resep SQL Inti (peer stats & flags)

**Peer stats + z-score (DuckDB/SQL lain):**
```sql
WITH base AS (
  SELECT *,
    CONCAT(dx_primary_code,'|',severity_group,'|',facility_class,'|',province) AS peer_key
  FROM claims_normalized
),
peer AS (
  SELECT peer_key,
         AVG(amount_claimed) AS peer_mean,
         approx_quantile(amount_claimed,0.9) AS peer_p90,
         STDDEV_POP(amount_claimed) AS peer_std
  FROM base GROUP BY 1
)
SELECT b.*,
       p.peer_mean, p.peer_p90, p.peer_std,
       CASE WHEN p.peer_std IS NULL OR p.peer_std=0 THEN NULL
            ELSE (b.amount_claimed - p.peer_mean)/p.peer_std END AS cost_zscore
FROM base b JOIN peer p USING(peer_key);
```

**Flags cepat:**
```sql
SELECT *,
  (LOS <= 1 AND amount_claimed > peer_p90) AS short_stay_high_cost,
  (severity_group = 'ringan' AND amount_claimed > peer_p90) AS severity_mismatch
FROM claims_scored;
```

**Duplicate window ≤ 3 hari:**
```sql
WITH w AS (
  SELECT a.claim_id,
    EXISTS(
      SELECT 1 FROM claims_normalized b
      WHERE b.patient_key=a.patient_key
        AND b.dx_primary_code=a.dx_primary_code
        AND COALESCE(b.procedure_main,'')=COALESCE(a.procedure_main,'')
        AND b.claim_id<>a.claim_id
        AND ABS(julianday(b.episode_date)-julianday(a.episode_date))<=3
    ) AS duplicate_pattern
  FROM claims_normalized a
)
SELECT * FROM w;
```

---

## 4) LLM Recipe (Audit Summary)

### 4.1 Input JSON (minimal)
```json
{
  "claim_id":"FKL02-123",
  "dx":{"code":"B50","name":"Plasmodium falciparum malaria"},
  "facility":{"class":"C","ownership":"Pemkab","province":"Papua"},
  "episode":{"admit":"2022-01-02","discharge":"2022-01-02","los":0},
  "finance":{"claimed":2218100,"paid":2218100,"gap":0},
  "peer":{"key":"B50|ringan|C|Papua","p90":1600000,"z":2.7},
  "flags":["short_stay_high_cost","high_cost_full_paid"],
  "dx_secondary":["E11","I10"]
}
```

### 4.2 Prompt Template (deterministik, ringkas)
```
SYSTEM:
Anda adalah asisten audit klaim kesehatan. Gunakan hanya field yang diberikan.
Jangan menebak fakta yang tidak ada. Jawab ringkas dalam bahasa Indonesia.

USER:
Susun ringkasan audit untuk klaim berikut, 6 bagian:
1) Identitas singkat (dx, kelas RS, wilayah, LOS).
2) Ringkasan biaya (claimed, paid, gap).
3) Perbandingan peer (peer_key, p90, z-score) 1 kalimat.
4) Alasan flag (sebut nama flag + 1 kalimat penjelasan per flag).
5) Potensi risiko (1 kalimat, gunakan kata “indikasi”).
6) 3–5 pertanyaan tindak lanjut untuk auditor.

Data:
<JSON>
```

**Parameter saran**: `temperature=0.2`, `max_tokens=300`.  
**Caching**: cache per `claim_id` + versi data; regen hanya jika field berubah.

### 4.3 Tooltip (hard-coded, tanpa LLM)
- `short_stay_high_cost` → “LOS ≤ 1 hari, biaya > P90 peer group.”
- `severity_mismatch` → “Severity ‘ringan’, biaya > P90 diagnosis-severity setara.”
- `duplicate_pattern` → “Kunjungan/prosedur serupa dalam ≤3 hari untuk pasien sama.”
- `high_cost_full_paid` → “Klaim besar dibayar hampir penuh.”

---

## 5) Operasional & Versi
- **Top-N policy**: default audit **Top 3%** risk_score (configurable).
- **Versi rules**: `RULESET_v1` (simpan di hasil & audit log).
- **Safety**: tidak menentukan “fraud pasti”; output = **indikasi untuk ditinjau**.
- **Logging wajib**: `claim_id, risk_score, flags[], RULESET_VERSION, generated_at`.

## 6) Implementasi Backend (Patch 1.1)
- Endpoint `GET /claims/{id}/summary` menghasilkan ringkasan deterministik mengikuti template di atas (6 bagian + follow-up question) sembari menunggu integrasi LLM eksternal.
- Endpoint `POST /claims/{id}/feedback` menyimpan keputusan auditor (`approved|partial|rejected`, `correction_ratio`, `notes`) ke tabel `audit_outcomes`.
- Response summary menyertakan metadata skor (`risk_score`, `rule_score`, `ml_score_normalized`), flag aktif, peer stats, serta `latest_feedback` bila ada.
- `app/services/audit_copilot.py` menjadi referensi utama implementasi backend; siap diganti ke call LLM (OpenAI/Bedrock) ketika kredensial tersedia.
