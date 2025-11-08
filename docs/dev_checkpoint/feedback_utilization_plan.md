# Rencana Pemanfaatan Feedback Auditor

Tanggal: 7 Nov 2025  
PIC: Rido Maulana (user)

Tujuan: memastikan catatan auditor (`audit_outcomes`) dipakai untuk monitoring kualitas model/rules dan menjadi bahan eksperimen supervised setelah label mencukupi.

---

## 1. Dataset Monitoring

### 1.1 Struktur Data
- Sumber: tabel `audit_outcomes` + `claims_scored` (risk/rule/ML) + metadata copilot/chat.
- View DuckDB: `claims_feedback_monitor` berisi kolom:
  - `claim_id`, `dx_primary_code`, `facility_class`, `province`.
  - `risk_score`, `rule_score`, `ml_score_normalized`, `flags`.
  - `decision` (approved/partial/rejected), `correction_ratio`, `notes`.
  - `reviewer_id`, `created_at`.
- Output disimpan sebagai Parquet `instance/data/claims_feedback_monitor.parquet` + tabel DuckDB untuk analitik cepat.

### 1.2 Pipeline
1. Jalankan script `python -m ml.pipelines.build_feedback_dataset` (baru) setelah auditor mengirimkan batch feedback.
2. Script membaca `audit_outcomes`, join dengan `claims_scored`, tulis ke view/tabel + Parquet.
3. File ini jadi sumber dashboard monitoring (precision @ feedback, proporsi klaim partial/rejected per flag).

---

## 2. Outline Eksperimen Supervised

### 2.1 Trigger & Target
- Mulai eksperimen ketika jumlah feedback `partial/rejected` ≥ 5k klaim unik agar data cukup.
- Target: model klasifikasi biner `fraud_like` (1 jika feedback ≠ approved, 0 jika approved).

### 2.2 Pipeline Eksperimen
1. **Dataset**  
   - Gunakan view `claims_feedback_monitor`, pilih kolom fitur standar (LOS, amount, peer stats, flags) + label `fraud_like`.
   - Handle imbalance via weighting atau sampling.
2. **Modeling**  
   - baseline: gradient boosting / logistic regression.  
   - metrics: `PR-AUC`, `Precision@K`, `Recall@K`.
3. **Evaluation & Rollout**  
   - Bandingkan dengan skor isolasi existing (`iso_v2`).  
   - Jika hasil signifikan (mis. PR-AUC naik ≥10%), simpan artefak `iso_supervised_v1` dan sebutkan di `model_meta`.
4. **Integraasi**  
   - `app/services/risk_scoring.py` membaca skor supervised sebagai komponen tambahan (mis. ensembel `max(ml_unsup, ml_sup)` atau weighted sum).

### 2.3 Dokumentasi
- Setiap run eksperimen dicatat di `docs/dev_checkpoint/experiments_log.md` (baru) dengan tanggal, jumlah label, metrik, keputusan.

---

## 3. Checklist Demo Hackathon
1. Tunjukkan endpoint `/claims/{id}/feedback` dan jelaskan bahwa data tersimpan di `audit_outcomes`.
2. Jelaskan view `claims_feedback_monitor` (diagram/pseudocode).
3. Paparkan rencana supervised di atas sebagai “next step” ketika label mencukupi.
4. Highlight bahwa FE chat + feedback form sudah siap, sehingga siklus data → AI → feedback → AI berikutnya dapat berjalan.
