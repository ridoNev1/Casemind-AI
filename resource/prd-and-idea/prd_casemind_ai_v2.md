# Product Requirements Document — Casemind AI Auditor (v2)

Tanggal: 10 Nov 2025  
PIC: Rido Maulana

## 1. Latar Belakang
- Auditor BPJS harus menyeleksi jutaan klaim; proses manual lambat dan rentan salah prioritas.
- Sistem Casemind menyatukan skor aturan + ML + copilot generatif agar auditor langsung melihat klaim berisiko tinggi.
- Versi sebelumnya hanya menampilkan daftar klaim; versi terbaru menambahkan sinkronisasi filter ke URL, badge reviewed, feedback loop, dan insight tarif.

## 2. Tujuan
1. Mempercepat identifikasi klaim tinggi risiko (time-to-first-review < 2 menit).  
2. Mengumpulkan outcome audit (feedback) minimal 70% dari klaim prioritas.  
3. Menyediakan insight tarif/peer di level klaim untuk memudahkan verifikasi biaya.  
4. Menyiapkan kerangka untuk integrasi report lainnya (severity mismatch, duplication).

## 3. KPI
- % klaim yang memiliki status Reviewed dalam 24 jam.  
- Jumlah prompt chat per auditor (proxy penggunaan copilot).  
- Jumlah insight tarif yang ditampilkan per sesi.  
- Error rate API <2% (non-auth).  
- Waktu load drawer detail < 2s median.

## 4. Scope Fungsional
### 4.1 Dashboard High-Risk
- Filter lengkap: severity, service type, facility class, page size, admit/discharge date range, province, kode DX, min/max risk score, min ML score, refresh cache.
- Semua filter + klaim terpilih disimpan di query string.
- Tabel menampilkan flagged claim lebih dahulu, plus badge Reviewed/Pending berdasar `latest_feedback`.

### 4.2 Drawer Detail
- Ringkasan klaim dari `/claims/{id}/summary` (sections, peer, flags, narrative).
- Tariff insight card dari `/reports/tariff-insight` (gap total, avg gap, ratio, dx group).  
- Feedback form (decision, correction ratio, notes) → `POST /claims/{id}/feedback`.

### 4.3 Chat Copilot
- `GET/POST /claims/{id}/chat` untuk histori & interaksi.  
- Quick prompt chips (saat ini isi input; hooking langsung ke API di backlog).  
- Loading state per bubble, scroll to latest.

### 4.4 Backend Enhancements
- `/claims/high-risk` enriched with `latest_feedback` + sorting flagged>non-flagged.  
- Tariff insight endpoint memfilter berdasar facility/severity/service/dx group.  
- ML pipeline memuat artefak anomaly detection; risk score = max(rule_score, ml_score_normalized).

## 5. Out of Scope (v2)
- Feedback history log (lebih dari 1 outcome).  
- Quick prompt hooking full + tool visualization.  
- Report severity mismatch/duplicates di dashboard.  
- Autoretrain model ML.

## 6. User Journey
1. Login → landing di dashboard high-risk (filter default).  
2. Auditor ubah filter (URL update).  
3. Click klaim → drawer muncul, ringkasan + tariff insight + feedback form.  
4. Auditor chat dengan copilot untuk verifikasi.  
5. Submit feedback → badge di tabel berubah jadi Reviewed.  
6. Auditor bisa share URL ke rekan (state filter tetap).

## 7. Risiko & Mitigasi
| Risiko | Dampak | Mitigasi |
| --- | --- | --- |
| Query DuckDB berat | UI lambat | LIMIT + filter + warning truncated |
| Tariff insight kosong | Pengguna bingung | Fallback message & refresh button |
| State URL terlalu panjang | Share link rusak | Normalisasi hanya parameter non-default |
| Refresh cache memakan memori | API down | Hanya expose toggle, doc peringatan, CLI refresh utama |

## 8. Rencana Iterasi (Next)
- Tambah report severity mismatch/duplicate ke section cards.  
- Quick prompt hooking ke copilot API + spinner per bubble.  
- Feedback history log + filter Reviewed di tabel.  
- Accordion/tab di drawer jika report makin banyak.

