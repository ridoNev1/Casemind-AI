# Frontend Implementation Guide — Casemind AI (Hackathon Scope)

Tanggal: 9 Nov 2025  
PIC: Rido Maulana (user)

Dokumen ini menjadi acuan teknis bagi tim Frontend saat membangun dashboard auditor + chat-based copilot. Seluruh endpoint sudah tersedia di backend Railway (`https://casemind-ai-production.up.railway.app`). Gunakan panduan berikut agar alur FE selaras dengan desain BE.

---

## 1. Authentication & Session

- Gunakan endpoint:
  - `POST /auth/login { "email": "...", "password": "..." }` → response berisi `access_token`, `expires_at`, dan profil user.
  - `POST /auth/register` hanya diperlukan bila FE menyediakan UI registrasi (opsional).
- Simpan token di `localStorage` atau `sessionStorage` (sesuai kebijakan). Setiap request berikutnya menambahkan header `Authorization: Bearer <token>`.
- Token berlaku ±1 jam (`JWT_ACCESS_EXPIRES_SECONDS`); jika menerima 401 dengan pesan “Token has expired”, redirect user ke login dan hapus token lokal.

---

## 2. Halaman & Layout

1. **Login (opsional, sesuai kebutuhan UI)**

   - Gunakan endpoint `POST /auth/login` (JWT) dengan email/password. Token disimpan di storage FE; semua request berikutnya menggunakan header `Authorization: Bearer <token>`.

2. **Halaman “High-Risk Claims”**

   - Layout split view:
     - **Panel kiri**: daftar klaim (table atau list) dengan kolom `claim_id`, `facility_name`, `dx_primary_label`, `amount_claimed`, `risk_score`, flags (chips).
     - **Panel kanan**: chat room + ringkasan klaim (lihat #3).
   - Filter bar di atas daftar memuat parameter:
     - `service_type` (dropdown), `severity` (dropdown), `facility_class` (dropdown), `start_date` & `end_date`, `discharge_start` & `discharge_end`, `province` (opsional).
     - Tombol “Reset filter” & “Refresh”.
   - Pagination: gunakan `page` dan `page_size` (default 50) sesuai response backend.

3. **Chat Room + Detail Klaim**

   - **Header Summary Card** (ambil dari `GET /claims/{id}/summary`):
     - Diagnosa, severity, service_type, LOS, biaya (claimed/paid/gap), risk_score, peer stats, flags.
   - **Thread**: bubble auditor (kanan) & copilot (kiri). History di-load dari `GET /claims/{id}/chat`.
   - **Input area**:
     - Textbox + tombol kirim (`POST /claims/{id}/chat`).
     - Quick prompt chips (lihat #5).
   - **Feedback panel**:
     - Form kecil (decision radio: approved/partial/rejected, correction_ratio optional, notes).
     - Submit ke `POST /claims/{id}/feedback`. Setelah sukses, tambahkan bubble “Feedback saved”.

4. **Opsional Reports/Analytics**
   - Jika FE ingin memanfaatkan laporan tarif atau mismatch (misal menampilkan modal), gunakan endpoint `/reports/tariff-insight` atau `/reports/severity-mismatch`.
   - Chart QC dapat membaca `GET /analytics/qc-status`.

---

## 3. Integrasi API

Base URL: `https://casemind-ai-production.up.railway.app`  
Header wajib: `Authorization: Bearer <jwt>` dan `accept: application/json`.

### 2.1 High-Risk Claims

```
GET /claims/high-risk
```

Query parameters:

- `page` (default 1), `page_size` (default 50, max 200).
- `severity`, `service_type`, `facility_class`, `province`, `dx`.
- `start_date`, `end_date` (filter admit date; format YYYY-MM-DD).
- `discharge_start`, `discharge_end`.
- `min_risk_score`, `max_risk_score`, `min_ml_score`.
- `refresh_cache` (true/false) — gunakan hanya jika ingin memaksa refresh skor ML (tidak untuk UI rutin).

Response:

```json
{
  "items": [...],
  "total": 1864,
  "page": 1,
  "page_size": 20,
  "model_version": "iso_v2",
  "ruleset_version": "RULESET_v1"
}
```

Catatan:

- Backend otomatis mengaplikasikan filter di DuckDB dan membatasi dataset via env `CLAIMS_MAX_QUERY_ROWS` (default 200k). FE tidak perlu menangani limit manual.
- `flags` adalah array string yang dapat dipakai untuk badge status.

### 2.2 Claim Summary

```
GET /claims/{claim_id}/summary
```

Digunakan sebagai header ringkasan (6 section + generative summary). Response memuat:

- `sections[]` (Identitas, Ringkasan biaya, Peer, Alasan flag, Potensi risiko, Pertanyaan tindak lanjut).
- `generative_summary` (teks markdown) — opsional jika LLM aktif.
- `claim` object (dx label, LOS, biaya).
- Metadata LLM di `llm`.

### 2.3 Chat History & Interaksi

```
GET /claims/{claim_id}/chat
POST /claims/{claim_id}/chat { "message": "...." }
```

Response POST:

```json
{
  "data": {
    "user_message": {...},
    "bot_message": {...}
  }
}
```

`bot_message.metadata` mencantumkan provider/model. FE harus append kedua bubble ke thread dan scroll ke bawah.

### 2.4 Feedback

```
POST /claims/{claim_id}/feedback
{
  "decision": "partial",
  "correction_ratio": 0.35,
  "notes": "Butuh koreksi tarif obat."
}
```

Gunakan form dengan validasi (ratio optional 0–1).

### 2.5 Reports (opsional)

- `/reports/tariff-insight?province=...&facility_id=...&severity=...&service_type=...&dx_group=...`
- `/reports/severity-mismatch`
- `/reports/duplicates`

### 2.6 Docs & Testing

- Swagger: `https://casemind-ai-production.up.railway.app/docs/swagger`
- OpenAPI JSON: `https://casemind-ai-production.up.railway.app/docs/openapi.json`
- Health: `GET /health/ping`

---

## 4. UX Flow Singkat

1. Auditor login → diarahkan ke halaman High-Risk.
2. Auditor memilih filter (default RITL + severity sedang).
3. Daftar klaim muncul, klik salah satu → FE:
   - Memanggil `GET /claims/{id}/summary`.
   - Memanggil `GET /claims/{id}/chat` (history).
   - Menampilkan panel chat + ringkasan.
4. Auditor bertanya di chat; FE kirim `POST /claims/{id}/chat`.
5. Setelah tuntas, auditor mengisi form feedback → FE panggil `POST /claims/{id}/feedback`.
6. FE menandai baris di list (mis. add icon “feedback submitted”) — bisa memakai `latest_feedback` dari summary atau memanggil history API jika perlu.

---

## 5. Quick Prompt Template (Chat)

Sediakan beberapa tombol/chips untuk mempercepat input auditor:

1. “Kenapa klaim ini dianggap fraud?”
2. “Bandingkan dengan peer group.”
3. “Bagaimana tarif RS ini?”
4. “Apa flag yang aktif & tindak lanjutnya?”
5. “Apa dokumen yang perlu saya cek?”

Masing-masing chip cukup mengisi textbox lalu auto-submit (FE boleh menambahkan prefix seperti “Tolong jelaskan ...”). Chat agent secara otomatis memanggil tools (`peer_detail_tool`, `flag_explainer_tool`, `tariff_insight_tool`) ketika mendeteksi kata kunci.

---

## 6. Error Handling

- Jika API mengembalikan 401, arahkan user ke login.
- Untuk 502/500 di Railway, tampilkan toaster “Silakan ulangi” dan otomatis retry sekali (kecuali 4xx).
- Chat POST dapat memakan waktu (LLM). Tampilkan spinner di bubble bot sampai respons diterima.
- Ketika `GET /claims/high-risk` mengembalikan `total=0`, tampilkan empty state (“Tidak ada klaim sesuai filter” + tombol reset filter).

---

## 7. Env & Config FE

Di FE `.env`:

```
VITE_API_BASE=https://casemind-ai-production.up.railway.app
```

Token JWT disimpan per session (localStorage/sessionStorage). FE tidak perlu menyimpan OpenAI key; semua panggilan LLM dilakukan oleh backend.

---

## 8. Referensi Dokumen

- Swagger/OpenAPI: `app/api/docs/routes.py` + `openapi.json`.
- Chat workflow detail: `docs/dev_checkpoint/chat_copilot_workflow.md`.
- Feedback plan (rencana monitoring/ML supervised): `docs/dev_checkpoint/feedback_utilization_plan.md`.
- Backend change log: `docs/dev_checkpoint/checkpoint_3_risk_api_integration.md`.

Dengan dokumen ini, tim FE memiliki gambaran jelas mengenai halaman yang diperlukan, integrasi API lengkap, serta pola interaksi chat copilot. Pastikan untuk selalu menggunakan JWT valid saat menguji endpoint di lingkungan Railway.
Mapping filter FE → query param:

| FE Filter        | Query Param                        | Contoh Value  |
| ---------------- | ---------------------------------- | ------------- |
| Severity         | `severity`                         | `sedang`      |
| Service Type     | `service_type`                     | `RITL`        |
| Facility Class   | `facility_class`                   | `RS Kelas C`  |
| Province         | `province`                         | `JAWA TENGAH` |
| DX Code          | `dx`                               | `J18`         |
| Admit Date Range | `start_date`, `end_date`           | `2022-11-01`  |
| Discharge Range  | `discharge_start`, `discharge_end` |               |
| Risk Range       | `min_risk_score`, `max_risk_score` | `0.6`         |
| ML Range         | `min_ml_score`                     | `0.7`         |
| Pagination       | `page`, `page_size`                |               |

Tips UX:

- Debounce filter input (200–300ms) sebelum memanggil API.
- Simpan filter di query string FE agar bisa dibagikan/shareable.
- Pastikan FE menampilkan `meta.total` sehingga auditor tahu banyaknya klaim yang tersedia.
  State management rekomendasi:
- `GET /claims/{id}/chat` dipanggil saat auditor membuka tab, hasil disimpan di store (pinia/redux) agar reload cepat.
- Jangan lupa handle loading/error per bubble. Jika POST gagal (mis. 502), tampilkan status failed di bubble bot dan sediakan tombol “Retry”.
