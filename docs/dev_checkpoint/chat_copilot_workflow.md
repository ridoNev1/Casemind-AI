# Chat-Based Audit Copilot Workflow

Tanggal: 7 Nov 2025  
PIC: Rido Maulana (user)

Dokumen ini menjabarkan rancangan UI agentic AI baru: auditor berpindah dari daftar klaim prioritas ke ruang obrolan (chat room) yang memusatkan ringkasan risiko, tanya-jawab LLM, dan pencatatan feedback.

---

## 1. Gambaran Umum

1. Auditor membuka `GET /claims/high-risk` (filter default RITL/berat, dsb.) untuk melihat daftar klaim prioritas.
2. Saat klaim dipilih, FE membuka **Chat Room** khusus claim_id tersebut.
3. Chat Room menampilkan:
   - **Ringkasan Klaim** (hasil endpoint `GET /claims/{id}/summary`) di atas conversation pane.
   - **Thread percakapan** antara auditor dan Audit Copilot (LLM). Bot otomatis mengirim ringkasan awal lalu siap menerima pertanyaan lanjutan.
   - **Input Prompt** di bagian bawah menyerupai UI chat; auditor mengetik pertanyaan atau instruksi (mis. “Tampilkan peer stats”, “Ada indikasi duplicate?”).
   - **Quick Action Buttons** untuk menyisipkan contoh prompt, menandai klaim, atau membuka laporan terkait.
4. Setelah auditor puas, ia mengirim keputusan (`approved|partial|rejected`, ratio koreksi, catatan) langsung dari panel yang sama. FE memanggil `POST /claims/{id}/feedback`; hasilnya dicatat di thread sebagai “Feedback saved”.

---

## 2. Detail Alur

| Langkah | Aksi Auditor | Aksi Sistem | API/Service |
| --- | --- | --- | --- |
| 1 | Pilih klaim di daftar high-risk | Memuat summary awal + memulai sesi chat | `GET /claims/{id}/summary` (Audit Copilot) |
| 2 | Ajukan pertanyaan lanjutan di chat | Bot menerjemahkan pertanyaan ke query (analytics/report) & balas jawaban | `app/services/analytics.py`, `app/services/reports.py` |
| 3 | Minta rekomendasi dokumen | Bot menggunakan flag/pertanyaan default untuk menyarankan checklist | audit_copilot heuristics/LLM |
| 4 | Submit keputusan audit | UI memanggil feedback API & menampilkan konfirmasi | `POST /claims/{id}/feedback` |
| 5 | Akhiri sesi | Bot menulis ringkasan percakapan + tautan follow-up | Audit Copilot + FE log |

---

## 3. Layout Komponen Chat Room

1. **Header Summary Card**
   - Diagnosa, kelas RS, provinsi, LOS.
   - Ringkasan biaya (claimed/paid/gap) + peer stats + risk score.
   - Flag aktif dan pertanyaan tindak lanjut.
2. **Conversation Thread**
   - Bot bubble pertama: ringkasan audit + highlight risiko.
   - Auditor bubble: pertanyaan manual atau quick action.
   - Bot bubble: jawaban generatif berdasarkan data (atau fallback deterministik jika LLM off).
   - Log sistem: “Feedback tersimpan”, “Laporan tarif dibuka”, dsb.
3. **Input & Controls**
   - Textbox + tombol kirim.
   - Attachment/quick prompt (mis. “Ringkas biaya”, “Tampilkan peer detail”, “Generate checklist dokumen”).
   - Dropdown keputusan audit (muncul saat auditor klik “Submit Feedback”).

---

## 4. API & Integrasi

- **Daftar klaim**: `GET /claims/high-risk` dengan filter severity/service_type, pagination.
- **Summary + LLM**: `GET /claims/{id}/summary` (mengembalikan `sections`, `generative_summary`, metadata LLM).
- **Feedback**: `POST /claims/{id}/feedback`.
- **Chat history**: 
  - `GET /claims/{id}/chat` → mengembalikan array pesan (auditor/bot) tersimpan di Postgres.
  - `POST /claims/{id}/chat` → menyimpan bubble baru (FE memanggil setiap kali pesan terkirim/diterima). Struktur kolom tabel `chat_messages`: `id`, `claim_id`, `sender`, `role`, `content`, `metadata`, `created_at`.
- **Analytics/Reports** (opsional quick replies): `GET /analytics/casemix`, `/reports/severity-mismatch`, `/reports/tariff-insight`.
- **Cache LLM**: `instance/cache/copilot/` – invalidasi saat data klaim berubah atau sesi chat dimulai ulang.
- **LangChain Tooling**:
  - `peer_detail_tool` – mengembalikan mean/P90/z-score peer group klaim yang sedang ditinjau; otomatis dipakai ketika auditor meminta perbandingan biaya.
  - `flag_explainer_tool` – menjelaskan flag rules aktif + statistik kemunculannya di dataset.
  - `tariff_insight_tool` – merangkum gap tarif fasilitas/dx terkait klaim (mengambil data dari laporan agregat).

---

## 5. Pekerjaan Implementasi

1. **Frontend**
   - Buat halaman “High-Risk Claims” dengan panel kiri (list) & kanan (chat).
   - Terapkan komponen chat (thread, input, quick action, feedback modal).
   - Sinkronisasi status (loading summary, menunggu jawaban LLM, dsb.).
2. **Backend Enhancements**
   - ✅ Persist chat ke Postgres (`chat_messages`) + expose endpoint `GET/POST /claims/{id}/chat`.
   - ✅ Gunakan `langchain-openai` sebagai orchestrator agent: `ChatOpenAI` + memory dari `chat_messages`, plus tool dasar (summary) — tool analytics lanjutan dicatat sebagai pengembangan berikutnya.
   - Tambah optional streaming/websocket bila openAI streaming diaktifkan.
   - ✅ Dokumentasikan API chat di Swagger (contoh request/respon chat + format history).
   - Siapkan helper untuk memetakan intent chat ke call analytics/reports (ditandai backlog lanjutan).  
   - **Catatan**: Feedback auditor tetap dikirim lewat form khusus (endpoint `POST /claims/{id}/feedback`) agar keputusan terstruktur; percakapan chat tidak otomatis menulis feedback ke database.
3. **Demo Script**
   - Langkah CLI/cURL: refresh klaim → `GET /claims/high-risk` → `GET /claims/{id}/summary` → `POST /claims/{id}/chat` → `POST /claims/{id}/feedback`. 
   - Narasi untuk presentasi: “Pilih klaim → bot kirim ringkasan → auditor bertanya → submit keputusan.”
4. **Monitoring**
   - Log percakapan disimpan (opsional) untuk analisis kualitas.
   - Feedback entry otomatis ditandai di conversation agar agen berikut tahu status terbaru.
   - Ekspos endpoint audit (mis. `GET /claims/{id}/chat/export`) jika diperlukan review regulator.

Dengan desain ini, pengalaman auditor menjadi percakapan tunggal: mereka tidak lagi lompat antar halaman untuk ringkasan, laporan, dan feedback—semuanya berada dalam satu chat room agentic AI.
