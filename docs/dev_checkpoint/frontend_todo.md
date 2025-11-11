# Frontend TODO — 10 Nov 2025

## In-flight
- Tariff insight card sudah muncul di drawer, tapi belum ada tab/accordion; evaluasi UX jika report lain ditambahkan.

## Next High Priority
1. **Integrasi report lanjutan**
   - Severity mismatch / duplicate report summary pada section cards.
   - Tambahkan endpoint `/reports/severity-mismatch` ke dashboard (overview kartu).
2. **Quick prompt hooking**
   - Saat chip ditekan, langsung kirim query ke `/claims/{id}/chat` + tampilkan spinner per bubble.
3. **Feedback history**
   - Ambil daftar audit outcome (butuh endpoint BE) dan render log di drawer.
4. **Reviewed filter**
   - Toggle/table filter untuk melihat hanya klaim pending atau reviewed.

## Nice-to-have
- Persist drawer tab state (Ringkasan vs Insight vs Chat) agar scroll pendek.
- Tooltip pada badge flag/status.
- Export CSV dari filter aktif.
- Empty state illustration + onboarding copy.

## Notes
- Semua filter + selected claim sudah tersimpan di URL.
- Reviewed badge di tabel mengambil `latest_feedback` yang dihydrate oleh BE.
- Drawer memuat summary, tariff insight, feedback form; chat ada di sheet terpisah.
