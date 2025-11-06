# Development TODO

Terakhir diperbarui: 6 Nov 2025  
PIC: Rido Maulana (user)

## ETL & Rules
- ✅ Map ID faskes unik + isi ulang label ICD yang kosong (pipeline kini menambah `facility_id`, `facility_name`, `facility_match_quality` = exact/regional/unmatched, serta fallback label ICD resmi).
- ✅ Catat metadata run ETL (`etl_runs`) termasuk versi ruleset/model setiap eksekusi.
- ✅ Integrasikan pipeline ETL dengan service risk scoring (otomasi refresh setelah build).

## Metadata & Logging
- ✅ Tabel `ruleset_versions` + `etl_runs` + `ml_model_versions` otomatis terisi saat ETL / refresh ML (menyimpan juga `top_k_snapshot` untuk insight audit).
- ✅ Dokumentasikan strategi verifikasi periodik (sampling manual + QC summary).

## ML & Artefak
- ✅ Definisikan schema/validation fitur (numeric/kategorikal) agar konsisten antara ETL, training, dan inference.
- Lengkapi hashing/anonymisation pipeline bila ada sumber data tambahan.

## Operasional & Monitoring
- ✅ Jadwalkan refresh ML otomatis via opsi `--refresh-ml` (integrasi dengan script ETL).
- ✅ Bangun dashboard berbasis `ml_scores_qc_summary.json` (heatmap provinsi, proporsi flag, tren LOS).
- ✅ Sediakan endpoint `/analytics/qc-status` untuk FE (alert validator/ops tinggal konsumsi endpoint ini).

## Product & API Enhancements
- ✅ Tambah filter tanggal pulang (`discharge_start`/`discharge_end`) pada `/claims/high-risk`.
- ✅ Tambahkan endpoint reporting lanjutan (`/reports/tariff-insight`) sesuai prioritas auditor.

## Copilot & Feedback
- Integrasikan provider LLM (OpenAI/Bedrock) beserta caching hasil agar summary dapat generatif.
- Manfaatkan catatan auditor sebagai dataset monitoring dan mulai eksperimen model supervised begitu label mencukupi.
