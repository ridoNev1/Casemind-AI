# Product Requirements Document — Casemind AI Auditor

Tanggal: 10 Nov 2025  
PIC: Rido Maulana

---

## 1. Latar Belakang & Tujuan
- BPJS membutuhkan alat audit klaim berbasis AI agar auditor bisa memprioritaskan klaim risiko tinggi tanpa membaca data CSV besar secara manual.
- Sistem backend sudah menyajikan data DuckDB + skor ML (risk score, flag rules) serta copilot untuk menjelaskan klaim.
- Tujuan PRD ini adalah menyelaraskan scope terbaru: dashboard high-risk, detail drawer, chat copilot, feedback loop, dan rencana integrasi report/analytics berikutnya.


## 2. Sasaran & KPI
1. **Time-to-first-review** turun ≥30% (auditor menemukan klaim yang layak audit < 2 menit).
2. **Coverage feedback** ≥70% klaim prioritas memiliki audit outcome tercatat per batch.
3. **Adoption**: minimal 10 auditor aktif/hari saat demo.
4. **Copilot helpfulness**: ≥70% interaksi tidak memerlukan re-ask (proxy via quick prompt atau survey).


## 3. Persona & Use Case
| Persona | Kebutuhan | Fitur Utama |
| --- | --- | --- |
| Auditor BPJS | Daftar klaim berisiko + filter cepat | Dashboard high-risk dengan penyortiran berbasis flag & risk score |
| Lead Auditor | Melihat status review & feedback | Badge Reviewed/Pending, form feedback, log |
| Data Ops | Memicu refresh ML jika diperlukan | Toggle `refresh_cache`, panel insight tarif (coming soon) |


## 4. Ruang Lingkup Fungsional
### 4.1 Dashboard High-Risk
- Filter: severity, service type, facility class, admit/discharge date range, province, ICD code, min risk/ML score, page size, refresh cache.
- Tabel: claim id, diagnosis, facility, biaya, risk score, flags, status (Reviewed / Pending). Klik row → membuka drawer detail+chat.
- Pagination: server-side, 20/50/100 baris.
- State disinkronkan ke URL (`page`, filter, `selected` claim).

### 4.2 Detail Drawer
- Ringkasan klaim (biaya, peer, flag, sections identitas/peer/risk).
- Feedback form (decision, correction_ratio, notes) → POST `/claims/{id}/feedback`, update `latest_feedback`.
- Tarik data summary dari `/claims/{id}/summary`. (TODO: panel insight tarif & report severity mismatch).

### 4.3 Chat Copilot
- Histori dari `/claims/{id}/chat`, bubble user/bot, loader saat pending.
- Input + quick prompt chips (pending hooking).
- Mutation POST chat dengan invalidasi query.

### 4.4 Backend Enhancements
- `/claims/high-risk` kini menyertakan `latest_feedback`.
- Sorting mendahulukan klaim ber-flag & risk score tinggi.

### 4.5 Roadmap Next
1. **Tariff Insight Panel**: GET `/reports/tariff-insight` menggunakan context klaim.
2. **Severity mismatch / duplicates dashboard**: Section cards summary.
3. **Feedback history list** (per claim) + export.
4. **Quick prompt hooking** ke copilot API.


## 5. Non-Fungsional
- **Responsif**: UI jalan minimal di layar laptop 1280px, panel drawer scrollable.
- **Perf**: Query default ≤ 2s per request (Gunicorn + DuckDB).
- **Reliability**: Simpan filter di URL; refresh browser tidak menghapus state.
- **Security**: Semua endpoint lewat JWT Bearer (disiapkan di backend).


## 6. Dependensi
- Data DuckDB (`/data/analytics.duckdb`) + cache ML scores.
- OpenAI key untuk copilot dan simulator LLM (opsional).
- Postgres untuk feedback/chat logs.


## 7. Risiko & Mitigasi
| Risiko | Dampak | Mitigasi |
| --- | --- | --- |
| Volume klaim terlalu besar → query lambat | UX drop | `CLAIMS_MAX_QUERY_ROWS`, filter default, pagination |
| Feedback form invalid (ratio >1) | API error | Validasi zod + pesan error sonner |
| LLM request lambat | Chat spinner lama | Quick prompt & status indicator (todo) |


## 8. Rencana Rilis
1. **Sprint 1** (done): Dashboard + filters + auth + detail drawer + chat.
2. **Sprint 2** (now): URL persistence, reviewed badge, feedback form, backend `latest_feedback`.
3. **Sprint 3** (next): Reports/analytics integration, quick prompts, history log.


## 9. Sukses Kriteria Per Fitur
- Dashboard: filter bekerja & sinkron URL, sorting flagged > non-flagged.
- Detail drawer: data summary tampil <1s setelah klik, feedback tersimpan.
- Chat: kirim/terima dengan indikator loading.
- Reports (next): insight siap pakai di drawer (tariff/peer).


## 10. Appendix
- Backend base URL: `https://casemind-ai-production.up.railway.app`.
- Github repos: `bpjs-be` (Flask), `bpjs-fe` (Next 16 + shadcn).
- Env penting: `CLAIMS_MAX_QUERY_ROWS`, `DUCKDB_PATH`, `NEXT_PUBLIC_API_BASE_URL`.

