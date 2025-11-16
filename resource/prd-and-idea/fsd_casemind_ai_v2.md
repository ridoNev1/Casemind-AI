# Functional Specification Document — Casemind AI Auditor (v2)

Tanggal: 10 Nov 2025  
PIC: Rido Maulana

## 1. Arsitektur Singkat
- FE: Next.js 16 + shadcn UI + React Query + Zustand, di folder `bpjs-fe`.
- BE: Flask + DuckDB + Postgres + MLScorer di folder `bpjs-be`.
- Auth: JWT Bearer (`/auth/login`).  
- Base URL API: `https://casemind-ai-production.up.railway.app`.

## 2. Modul Frontend
### 2.1 Filter High-Risk
- Komponen: `app/page.tsx`, `components/data-table.tsx`.
- State filter disimpan di URL via `useSearchParams`. Parameter yang dipakai: `page`, `page_size`, `severity`, `service_type`, `facility_class`, `province`, `dx`, `start_date`, `end_date`, `discharge_start`, `discharge_end`, `min_risk_score`, `max_risk_score`, `min_ml_score`, `refresh_cache`.
- Reset filter → default (severity sedang, RITL, page_size 20).  
- API: `GET /claims/high-risk` dengan query tersebut.

### 2.2 Tabel Klaim
- Menggunakan TanStack Table + highlight row + badge status.  
- Kolom: #, Klaim (ID + diagnosis + LOS + tanggal), Fasilitas & Wilayah, Severity/Service, Biaya (claimed/paid), Risk Score, Flags, Status.  
- Sort backend (flag count + risk score).  
- Klik row → set `selectedClaimId` + open sheet.

### 2.3 Drawer Detail
- `ClaimDetailPanel` memanggil `GET /claims/{id}/summary`.  
- Menampilkan ringkasan, sections, flags, narratives, latest feedback.
- Tariff card: hook `useTariffInsight` memanggil `/reports/tariff-insight` (limit 3) berdasar context klaim. UI menampilkan gap total, avg gap, ratio, refresh button.
- Feedback form: `POST /claims/{id}/feedback` (decision, correction_ratio, notes). On success, refetch summary sehingga `latest_feedback` update.

### 2.4 Chat Panel
- `ClaimChatPanel` memanggil `GET /claims/{id}/chat`; `POST` untuk kirim pesan, dengan toasts & loading indicator. Chips prompt sudah ada, hooking ke API di backlog.

### 2.5 Badge Reviewed
- Table memeriksa `latest_feedback` dari `/claims/high-risk`. Jika ada → `Reviewed`, jika tidak → `Pending`.

## 3. Modul Backend Relevan
### 3.1 `/claims/high-risk`
- Parameter filter sesuai FE.  
- Sorting: flagged first → flag count → risk score desc.  
- Response item menyertakan `latest_feedback` (diambil dari `AuditOutcome`).

### 3.2 `/claims/{id}/summary`
- Menghasilkan summary sections, generative summary, peer info, flags, follow-up questions, latest feedback.

### 3.3 `/claims/{id}/feedback`
- Validasi decision ∈ {approved, partial, rejected}.  
- Menyimpan outcome ke Postgres; summary & list mengonsumsi data ini.

### 3.4 `/reports/tariff-insight`
- Query parameter: `province`, `facility_id`, `severity`, `service_type`, `dx_group`, `limit`.  
- Mengembalikan list insight (claim_count, total_claimed, total_gap, avg_gap, avg_payment_ratio, dll).  
- Digunakan FE untuk card insight.

### 3.5 `/claims/{id}/chat`
- GET history, POST append + panggil copilot (LLM + tools).  
- Tools yang tersedia: peer detail, flag explainer, tariff insight.  
- Response memuat metadata provider/model.

## 4. Data & ML
- `claims_normalized` (DuckDB) berisi klaim + dx, biaya, peer, flags.  
- ML scoring: artefak anomaly detection (Isolation Forest) disimpan di `ml/inference`.  
- Risk score = max(rule score, ml_score_normalized).  
- Simulator synthetic claims: CLI `python -m ops.simulation.run_simulator` menghasilkan data ke `claims_live_stream` (opsional feed).

## 5. UI Flow Detail
1. Login → dashboard.  
2. Auditor atur filter → URL update.  
3. Klik klaim → sheet terbuka, summary + insight + feedback + chat.  
4. Submit feedback → toast + badge update.  
5. Tariff card menampilkan insight; bisa refresh manual.  
6. Chat digunakan untuk Q&A; quick prompt hooking next iteration.

## 6. Ekspektasi UX
- Drawer max height 60vh (scroll).  
- Skeleton untuk summary & tariff ketika loading.  
- Toast error jika API gagal (Sonner).  
- Filter button disabled saat sinkronisasi (optional).  
- Table badge & highlight row memudahkan tracking review status.

## 7. Backlog & Ide
- Tambah tab/accordion agar drawer tidak terlalu panjang.  
- Quick prompt auto-send + spinner per bubble.  
- History feedback list.  
- Report severity mismatch/duplicate di dashboard.  
- Export/print summary PDF.  
- Admin toggle simulator.
