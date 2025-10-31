
# Casemind AI — Data Recipes (Public & Private)  
_Path: place in your repo at `/docs/data-recipes.md`_

**Tujuan**: Panduan teknis ringkas **bagaimana** semua resource data dipakai untuk menghasilkan output utama (list risiko, laporan mismatch, dsb.). Ikuti resep per output.

---

## Peta Cepat “Pakai Data Apa?”
| Output | FKRTL | Non‑Kap | Kepesertaan | Dx Sekunder | ICD‑10 | ICD‑9‑CM | RS/Wilayah | ICD‑O | Postman FHIR |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **A** High‑Risk List | ✅ | – | (ops) | ✅ | ✅ | (ops) | ✅ | – | – |
| **B** Claim + Audit Summary | ✅ | – | – | ✅ | ✅ | (ops) | ✅ | – | – |
| **C** Casemix by Province | ✅ | – | (ops) | – | (ops) | – | ✅ | – | – |
| **D** Severity Mismatch | ✅ | – | – | – | ✅ | – | ✅ | – | – |
| **E** Duplicate Pattern ≤3d | ✅ | – | – | – | ✅ | ✅ | – | – | – |
| **F** Tariff Insight Starter | ✅ | – | – | – | ✅ | – | ✅ | – | – |
| **G** KIA / Non‑Kap Monitor | – | ✅ | – | – | ✅ | – | ✅ | – | – |
| **H** Oncology Lens | ✅ | – | – | – | – | – | ✅ | ✅ | – |
| **I** Interop Check (FHIR) | (ref) | (ref) | (ref) | (ref) | – | – | – | – | ✅ |
| **J** Peer Comparison Card | ✅ | – | – | – | ✅ | – | ✅ | – | – |

> (ops) = opsional bila tersedia/berguna.  
> Public refs: **ICD‑10**, **ICD‑9‑CM**, **ICD‑O**, **Master Wilayah**, **Master RS**, **KFA**, **Postman/FHIR**.

---

## Resep Per Output (Langsung Pakai)

### A) High‑Risk Claims List (Top‑N)
**Tujuan**: daftar klaim berisiko + alasan.  
**Data**: FKRTL + Dx Sekunder + ICD‑10 + RS/Wilayah.  
**Langkah**  
1. Join FKRTL ↔ (ICD‑10 → `dx_primary_name`) ↔ RS (`facility_class, ownership`) ↔ Wilayah (`province`).  
2. Hitung:
   - `LOS = discharge_date - admit_date`
   - `peer_key = dx_primary + severity + facility_class + province`
   - `peer_p90, peer_mean, peer_std` per `peer_key`
   - `cost_zscore = (amount_claimed - peer_mean)/peer_std`
3. Flag rules:
   - `short_stay_high_cost`: `LOS<=1 && amount_claimed>peer_p90`
   - `severity_mismatch`: `severity='ringan' && amount_claimed>peer_p90`
   - `duplicate_pattern`: lihat E
   - `high_cost_full_paid`: `paid/claimed>=0.95 && cost_zscore>2`
4. `risk_score = max(rule_scores)` → sort desc.  
**API**: `GET /claims/high-risk?filters…`

---

### B) Claim Detail + Audit Summary (Co‑pilot)
**Data**: FKRTL (+ Dx Sekunder), ICD‑10, RS/Wilayah.  
1. Ambil klaim + `dx_secondary_codes[]`.  
2. Payload JSON (dx, LOS, biaya, peer_p90, z‑score, flags).  
3. Kirim ke LLM → ringkasan audit (tanpa PII).  
**API**: `GET /claims/{id}`, `GET /claims/{id}/summary`.

---

### C) Casemix by Province (KPI Wilayah)
**Data**: FKRTL, Wilayah, (ops) Kepesertaan.  
Group by `province`: `count, avg(LOS), median(claimed/paid), high_risk_rate`.  
**API**: `GET /casemix/aggregations?group_by=province`.

---

### D) Severity Mismatch Report
**Data**: FKRTL, ICD‑10, RS/Wilayah.  
Filter: `severity='ringan' AND amount_claimed>peer_p90`.  
**Kolom**: `claim_id, dx_primary, facility_class, province, LOS, claimed, peer_p90, delta%`.  
**API**: `GET /reports/severity-mismatch`.

---

### E) Duplicate Claims (Window ≤ 3 hari)
**Data**: FKRTL (+ `patient_key` hash), ICD‑10, ICD‑9‑CM.  
Kriteria mirip: `patient_key + dx_primary + procedure_main`, `|date_diff|<=3`.  
Set `duplicate_pattern=true`.  
**API**: `GET /reports/duplicates?days=3`.

---

### F) Tariff Insight Starter
**Data**: FKRTL, ICD‑10, RS/Wilayah.  
Group by `dx_primary + severity + facility_class (+ province)` →
`median(claimed) vs median(paid)`, `median LOS`, `outlier_rate`.  
**API**: `GET /tariff/insights?group=dx_severity_facility`.

---

### G) KIA / Non‑Kapitasi Monitoring
**Data**: Non‑Kapitasi, ICD‑10 (O*, Z36/Z39), Wilayah/RS.  
Filter ICD KIA → agregasi wilayah/fasilitas: `count, median paid, repeat visits`.  
**API**: `GET /kia/overview?province=…`.

---

### H) Oncology Lens (opsional)
**Data**: FKRTL, ICD‑O, RS/Wilayah.  
Map klaim onkologi → ICD‑O; agregasi biaya & LOS per morfologi/kelas RS.  
**API**: `GET /oncology/aggregations?morph=…`.

---

### I) Interop Check (FHIR/SATUSEHAT Blueprint)
**Data**: Postman SATUSEHAT/BPJS (FHIR schemas).  
Mapping: `claim_id→Claim.identifier`, `admit/discharge→Encounter.period`, `facility→Organization`, `amount_*→Claim/ClaimResponse`.  
**Manfaat**: istilah UI/API kita selaras standar nasional.

---

### J) Peer Comparison Card (per klaim)
**Data**: FKRTL, ICD‑10, RS/Wilayah.  
Render: “Peer = `B50|ringan|Kelas C|Papua` → P90=1.6M; Klaim=2.2M (+37%).”  
**API**: bagian dari `GET /claims/{id}`.

---

## 3 SQL Snippet Penting (DuckDB)
**Peer stats & z‑score**
```sql
WITH base AS (
  SELECT *,
    CONCAT(dx_primary_code,'|',severity_group,'|',facility_class,'|',province) AS peer_key
  FROM claims
),
peer AS (
  SELECT peer_key,
         AVG(amount_claimed) AS peer_mean,
         approx_quantile(amount_claimed,0.9) AS peer_p90,
         STDDEV_POP(amount_claimed) AS peer_std
  FROM base GROUP BY 1
)
SELECT b.*, p.peer_p90,
       CASE WHEN p.peer_std IS NULL OR p.peer_std=0 THEN NULL
            ELSE (b.amount_claimed - p.peer_mean)/p.peer_std END AS cost_zscore
FROM base b JOIN peer p USING(peer_key);
```

**Severity mismatch**
```sql
SELECT * FROM claims
WHERE severity_group='ringan' AND amount_claimed>peer_p90;
```

**Duplicate window (≤3 hari)**
```sql
SELECT a.claim_id, EXISTS(
  SELECT 1 FROM claims b
  WHERE b.patient_key=a.patient_key
    AND b.dx_primary_code=a.dx_primary_code
    AND COALESCE(b.procedure_code,'')=COALESCE(a.procedure_code,'')
    AND b.claim_id<>a.claim_id
    AND ABS(julianday(b.episode_date)-julianday(a.episode_date))<=3
) AS duplicate_pattern
FROM claims a;
```

---

## Catatan Teknis Singkat
- `patient_key` = **hash + salt** (tanpa PII).  
- Simpan hasil jadi satu tabel **`claims_normalized`** (1 baris = 1 episode).  
- Public refs dipakai untuk **label manusiawi** & **peer grouping** (ICD‑10/9, RS, Wilayah).  
- Output hanya agregasi/subset anonim untuk demo/pitch.

