# Product Requirements Document — Casemind AI (Revision 21 Nov 2025)

**PIC:** Rido Maulana  
**Stage:** Hackathon build → Pilot-ready FE/BE  
**Latest Update:** Sidebar/report FE shipped, tariff insight API online, simulator CLI siap.

---

## 1. Konteks & Referensi
Casemind AI menjawab kebutuhan pengawasan klaim JKN yang disebut di:
- ICISTECH 2021 (ketepatan kode INA-CBG memengaruhi akurasi pembayaran).  
- IJICC 2019 (risiko upcoding/upcoding berulang di sistem JKN).  
- ScienceDirect 2024 & JQPH 2020 (gap biaya riil vs tarif INA-CBG).  
- SATUSEHAT FHIR + KFA + master wilayah (standar struktur Claim/ClaimResponse, referensi obat/tarif nasional).

Intinya, audit manual tidak skala untuk jutaan klaim dan tidak ada satu sumber kebenaran untuk tarif/risiko. Casemind AI menggabungkan rule engine, ML tabular, dan LLM reasoning + dokumentasi standar agar auditor memiliki *single cockpit*.

---

## 2. Masalah Utama
1. **Fraud/upcoding & klaim duplikat** – LOS 0 hari namun biaya tinggi, diagnosis ringan ditagih berat, klaim sama muncul ≤3 hari.
2. **Mismatch tarif vs biaya riil** – RS tertentu underpaid, lainnya overpaid → sulit membuktikan tanpa agregasi nasional.
3. **Audit manual & inkonsisten** – Verifikator tiap wilayah memakai excel berbeda; tidak ada alasan flag terstandar.
4. **Kurang evidence untuk revisi tarif** – Data granular (severity, biaya diajukan/dibayar, peer) tidak siap pakai.

---

## 3. Data Fondasi
Sumber: sampel klaim BPJS 2015–2023 yang dianonimkan, plus referensi publik.
- **Klaim FKRTL/FKTP/non-kapitasi**: tanggal masuk/pulang, kelas RS, diagnosis ICD-10, prosedur ICD-9, severity, tarif INA-CBG, biaya diajukan vs dibayar.
- **Konteks peserta**: segmen (PBI/PBPU), kelas hak rawat, wilayah.
- **Diagnosis sekunder & prosedur**: pembeda kasus kompleks vs ringan.
- **Referensi nasional**: SATUSEHAT Claim/ClaimResponse, master faskes, master wilayah, KFA.
- **Normalisasi**: pipeline `claims_normalized` + DuckDB, siap query peer, severity, tarif.

---

## 4. Tujuan Produk (v2)
1. **Triage otomatis** klaim risiko tinggi dengan alasan jelas (<2 menit time-to-first-review).
2. **Audit insight siap pakai**: summary, tariff gap, chat copilot, feedback form dalam satu drawer.
3. **Monitoring nasional**: severity mismatch & duplicate report untuk regulator.
4. **Feedback loop**: tangkap keputusan auditor (approved/partial/rejected) sebagai dasar retraining ML tabular + LLM reasoning.

---

## 5. KPI & Guardrail
| KPI | Target Hackathon | Catatan |
| --- | --- | --- |
| Median load `/claims/high-risk` | < 2.5s | DuckDB filter + pagination + env `CLAIMS_MAX_QUERY_ROWS`. |
| % klaim dengan `latest_feedback` <24h | ≥60% | Gunakan badge Reviewed/Pending. |
| Chat adoption | ≥3 prompt/auditor/hari | Quick chips + sheet UX. |
| Tariff insight coverage | ≥70% klaim terpilih punya kartu | fallback copy bila kosong. |
| API error (non-auth) | <2% | Observed via console + server logs. |

Guardrail: jangan trigger refresh ML score via API (CLI only); simulator LLM dibatasi env `SIM_*` agar tidak memenuhi disk/ram.

---

## 6. Ruang Lingkup Fungsional
### 6.1 High-Risk Claims Console (FE `/`)
- Filter sinkron ke URL: severity, service_type, facility_class, page_size, admit/discharge range, province, dx, min/max risk, min ML, refresh toggle.
- Tabel menampilkan klaim dengan kolom #, klaim, fasilitas, severity/service, biaya, skor ML/rule, badge Reviewed/Pending (dari `latest_feedback`).
- Sorting default: flagged claims (ada `flags`) + skor tertinggi → sisanya.

### 6.2 Detail Drawer + Chat
- `GET /claims/{id}/summary` → sections, peer, flags, `latest_feedback` hydration.
- Tariff insight card (`GET /reports/tariff-insight` param facility/province/severity/service/dx). Fallback copy + refresh button.
- Feedback form (`decision`, `correction_ratio`, optional notes) → `POST /claims/{id}/feedback`, invalidasi summary, update badge.
- Chat sheet: `GET/POST /claims/{id}/chat`, suggestion chips, spinner per bubble.

### 6.3 Reports Page (`/reports`)
- Summary cards + tables untuk `/reports/severity-mismatch` dan `/reports/duplicates` dengan limit selector dan refresh.
- Tujuan: memberi konteks kebijakan (wilayah/RS mana outlier) tanpa meninggalkan dashboard utama.

### 6.4 Data Simulation CLI (Operator)
- `python -m ops.simulation.run_simulator --duration ...` untuk injeksi klaim sintetis (opsional LLM). Digunakan untuk demo volume.
- Dokumentasi di `docs/ops/data_simulation.md`; referensi command juga dicantumkan di PRD ini.

---

## 7. Experience Flow
1. **Login** (React Hook Form + Zod + Zustand). Token disimpan di storage, guard Auth memblokir halaman lain.
2. **Landing High-Risk**: default severity `sedang`, service `RITL`, page_size 20.
3. **Filter** → query string update; bisa dibagikan.
4. **Pilih klaim** → Drawer: summary, tariff insight, feedback form. Chat sheet bisa dibuka untuk percakapan AI.
5. **Submit feedback** → badge berubah Reviewed; data siap untuk tim governance.
6. **Buka Reports** → insight mismatch/duplicate; bisa kembali ke dashboard.

---

## 8. Arsitektur & Integrasi
- **Backend**: Flask + DuckDB; endpoints: `/claims/high-risk`, `/claims/{id}/summary`, `/claims/{id}/chat`, `/claims/{id}/feedback`, `/reports/*`.
- **Risk Engine**: rule score (flags: short_stay_high_cost, duplicate_pattern, dll) + ML anomaly score (`ml_score_normalized`). `risk_score = max(rule_score, ml_score_norm)`.
- **Chat Copilot**: LangChain + OpenAI (gpt-4o-mini) memanggil tools peer/tariff/flag. Caching metadata di DB.
- **FE**: Next.js App Router, shadcn UI, TanStack Query, Zustand auth store, Axios API client (JWT header). Layout: sidebar + sheet.
- **Simulasi**: CLI men-sample klaim nyata, mutate, optionally LLM (SIM_FORCE_LLM). Log di `instance/logs/simulation_runs.jsonl`.

---

## 9. Compliance & Privacy
- Data sudah dianonimkan (tidak ada NIK/nama). Analisis berbasis episode, bukan individu.
- Output hanya skor + alasan + insight; keputusan akhir tetap di auditor/regulator.
- Menyamai struktur SATUSEHAT Claim agar mudah dipetakan jika integrasi nasional diperlukan.

---

## 10. Stakeholder & Kebutuhan
| Stakeholder | Kebutuhan | Fitur yang Menjawab |
| --- | --- | --- |
| Auditor BPJS/NCC | Daftar klaim prioritas + alasan | Dashboard + drawer + chat |
| P2JK / Kendali Biaya | Insight mismatch & tarif | Reports page + tariff card |
| Tim tarif INA-CBG | Evidence under/over paid | Tariff insight + normalized dataset |
| RS/Dinkes | Transparansi posisi terhadap peer | Dashboard + future sharing |
| Tim Integrasi SATUSEHAT | Struktur data standar | Normalization layer + docs |

---

## 11. Roadmap Lanjutan
1. **Audit Workflow Portal**: tiket otomatis, history feedback, filter Reviewed/Pending, export CSV.
2. **Tariff Recalibration Engine**: aggregator LOS/severity/biaya per RS kelas & diagnosis → rekomendasi tariff gap.
3. **LLM Labeling Engine**: fine-tune reasoning + clinical pathway knowledge untuk auto-label (approved/partial/reject) sebagai pseudo-feedback sebelum feedback manusia cukup.
4. **Reports tambahan**: analytics severity vs cost, duplicates timeline, suspected facility ranking.
5. **Autosim + Scheduler**: cron simulation + incremental ML scoring tanpa OOM.

---

## 12. Deliverables Hackathon (✅ = sudah, 🔄 = in-progress)
- ✅ `/claims/high-risk` FE dengan filter URL, badge Reviewed, sorting flagged → highest risk.
- ✅ Drawer summary + tariff insight card + feedback form + chat sheet.
- ✅ `/reports` page dengan severity mismatch + duplicate table.
- ✅ Docs & simulator CLI instructions (`docs/ops/data_simulation.md`).
- 🔄 Quick prompt hooking ke jalur audit (opsional low priority).  
- 🔄 Feedback history & reviewed filter toggle (backlog).

---

Dengan PRD ini, tim FE/BE memiliki acuan terkini untuk melanjutkan pengerjaan (reports tambahan, audit workflow, integrasi ML). Seluruh referensi kebijakan/standar disertakan untuk menjaga keselarasan dengan mandat SATUSEHAT & BPJS.
