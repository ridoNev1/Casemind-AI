from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from flask import current_app

from ml.common.data_access import DataLoader
from ml.inference.scorer import MLScorer

from ..extensions import db
from ..models import AuditOutcome, User
from . import risk_scoring

FLAG_DESCRIPTIONS = {
    "short_stay_high_cost": "LOS ≤ 1 hari namun biaya melebihi P90 peer group.",
    "severity_mismatch": "Severity tercatat ringan tetapi biaya melewati P90 peer group.",
    "high_cost_full_paid": "Biaya tinggi dibayar hampir penuh (rasio ≥95%) dan z-score > 2.",
    "duplicate_pattern": "Ada klaim dengan DX/prosedur identik dalam ≤3 hari untuk pasien sama.",
}

FOLLOW_UP_QUESTIONS = {
    "short_stay_high_cost": [
        "Minta ringkasan medis atau log tindakan untuk membuktikan kebutuhan rawat tinggal singkat.",
        "Verifikasi apakah klaim seharusnya diproses sebagai rawat jalan.",
    ],
    "severity_mismatch": [
        "Tinjau kembali pengkodean severity dan diagnosa primer.",
        "Pastikan tarif paket sesuai severity yang tercatat.",
    ],
    "high_cost_full_paid": [
        "Periksa bukti pembayaran dan e-klaim untuk memastikan tidak ada tagihan ganda.",
        "Apakah audit internal Faskes memberikan catatan justifikasi biaya tinggi ini?",
    ],
    "duplicate_pattern": [
        "Konfirmasi dengan Faskes apakah kunjungan dalam rentang 3 hari merupakan episode tersendiri.",
        "Periksa apakah tindakan/prosedur tercatat ganda padahal hanya dilakukan sekali.",
    ],
}

DEFAULT_QUESTIONS = [
    "Apakah dokumentasi pendukung (resume medis, SEP, log tindakan) sudah lengkap?",
    "Apakah terdapat catatan audit sebelumnya terhadap klaim serupa dari Faskes yang sama?",
    "Perlu koordinasi lanjut dengan tim verifikator klinis terkait temuan ini?",
]

ALLOWED_DECISIONS = {"approved", "partial", "rejected"}


class ClaimNotFound(Exception):
    """Raised when the requested claim_id does not exist in analytics storage."""


class FeedbackValidationError(Exception):
    """Raised when feedback payload is invalid."""


@dataclass
class ClaimContext:
    claim_id: str
    data: pd.Series


def _format_currency(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"Rp {float(value):,.0f}".replace(",", ".")


def _format_ratio(value: Any) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value) * 100:.1f}%"


def _load_claim_context(claim_id: str) -> ClaimContext:
    loader = DataLoader()
    df = loader.load_claims_normalized(filters={"claim_id": claim_id})
    if df.empty:
        raise ClaimNotFound(f"Claim {claim_id} tidak ditemukan.")

    row = df.iloc[0:1].copy()

    score_df = pd.DataFrame()
    try:
        score_df = loader.query(
            f"SELECT * FROM {risk_scoring.SCORES_CACHE_TABLE} WHERE claim_id = ?",
            params=[claim_id],
        )
    except Exception:
        score_df = pd.DataFrame()

    if score_df.empty:
        try:
            scorer = MLScorer()
            score_df = scorer.score_dataframe(row)
        except FileNotFoundError:
            score_df = pd.DataFrame(
                {
                    "claim_id": [claim_id],
                    "ml_score": [None],
                    "ml_score_normalized": [None],
                    "model_version": ["unknown"],
                }
            )

    merged = row.merge(score_df, on="claim_id", how="left")
    enriched = risk_scoring._compute_rule_enrichment(merged)

    if "ml_score_normalized" not in enriched.columns:
        enriched["ml_score_normalized"] = None
    if "ml_score" not in enriched.columns:
        enriched["ml_score"] = None
    if "model_version" not in enriched.columns:
        enriched["model_version"] = "unknown"

    enriched["risk_score"] = enriched[["rule_score", "ml_score_normalized"]].max(axis=1).fillna(
        enriched["rule_score"].fillna(0)
    )

    return ClaimContext(claim_id=claim_id, data=enriched.iloc[0])


def _hydrate_flags(series: pd.Series) -> list[str]:
    flags = series.get("flags") or []
    if isinstance(flags, list):
        return flags
    if pd.isna(flags):
        return []
    return [str(flags)]


def generate_summary(claim_id: str) -> dict[str, Any]:
    """Build deterministic audit summary for a claim following the LLM recipe layout."""
    context = _load_claim_context(claim_id)
    row = context.data

    dx_label = row.get("dx_primary_label") or row.get("dx_primary_code") or "-"
    province = row.get("province_name") or "UNKNOWN"
    facility_class = row.get("facility_class") or "-"
    severity = row.get("severity_group") or "-"
    service_type = row.get("service_type") or "-"
    los = int(row["los"]) if not pd.isna(row.get("los")) else None

    amount_claimed = row.get("amount_claimed")
    amount_paid = row.get("amount_paid")
    amount_gap = row.get("amount_gap")
    peer_key = row.get("peer_key") or "-"
    peer_p90 = row.get("peer_p90")
    cost_zscore = row.get("cost_zscore")
    bpjs_ratio = row.get("bpjs_payment_ratio")

    flags = _hydrate_flags(row)
    risk_score = float(row.get("risk_score") or 0)
    rule_score = row.get("rule_score")
    ml_score = row.get("ml_score")
    ml_score_normalized = row.get("ml_score_normalized")
    model_version = row.get("model_version") or "unknown"
    ruleset_version = row.get("ruleset_version") or current_app.config.get("RULESET_VERSION", "RULESET_v1")

    ident_text = (
        f"Diagnosa {dx_label} (severity {severity}, layanan {service_type}) di {facility_class} – {province}. "
        f"LOS {los} hari." if los is not None else
        f"Diagnosa {dx_label} (severity {severity}, layanan {service_type}) di {facility_class} – {province}."
    )

    cost_text = (
        f"Klaim: { _format_currency(amount_claimed) }, dibayar { _format_currency(amount_paid) }, "
        f"gap { _format_currency(amount_gap) }."
    )

    peer_text = (
        f"Peer {peer_key} memiliki P90 { _format_currency(peer_p90) } dengan z-score { cost_zscore:.2f}."
        if peer_p90 and not pd.isna(cost_zscore)
        else f"Peer {peer_key} – statistik tidak lengkap."
    )

    flag_lines = [FLAG_DESCRIPTIONS.get(flag, flag.replace("_", " ")) for flag in flags]
    if not flag_lines:
        flag_lines = ["Tidak ada flag rules aktif."]
    flags_text = " ; ".join(flag_lines)

    if risk_score >= 0.8:
        risk_text = f"Indikasi risiko tinggi (risk_score {risk_score:.2f}); prioritaskan untuk audit mendalam."
    elif risk_score >= 0.5:
        risk_text = f"Indikasi risiko sedang (risk_score {risk_score:.2f}); butuh verifikasi detail biaya."
    else:
        risk_text = f"Indikasi risiko rendah (risk_score {risk_score:.2f}); cek sampel dokumen seperlunya."

    questions = []
    for flag in flags:
        questions.extend(FOLLOW_UP_QUESTIONS.get(flag, []))
    questions = list(dict.fromkeys(questions))
    if len(questions) < 3:
        for q in DEFAULT_QUESTIONS:
            if len(questions) >= 5:
                break
            if q not in questions:
                questions.append(q)
    if len(questions) > 5:
        questions = questions[:5]

    sections = [
        {"title": "Identitas singkat", "content": ident_text},
        {"title": "Ringkasan biaya", "content": cost_text},
        {"title": "Perbandingan peer", "content": peer_text},
        {"title": "Alasan flag", "content": flags_text},
        {"title": "Potensi risiko", "content": risk_text},
        {"title": "Pertanyaan tindak lanjut", "content": "; ".join(questions)},
    ]

    narrative = "\n".join(f"{idx+1}) {section['content']}" for idx, section in enumerate(sections))

    latest_feedback = (
        AuditOutcome.query.filter_by(claim_id=claim_id)
        .order_by(AuditOutcome.created_at.desc())
        .first()
    )

    return {
        "claim_id": claim_id,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "model_version": model_version,
        "ruleset_version": ruleset_version,
        "risk_score": risk_score,
        "rule_score": None if pd.isna(rule_score) else float(rule_score),
        "ml_score": None if pd.isna(ml_score) else float(ml_score),
        "ml_score_normalized": None if pd.isna(ml_score_normalized) else float(ml_score_normalized),
        "bpjs_payment_ratio": None if pd.isna(bpjs_ratio) else float(bpjs_ratio),
        "flags": flags,
        "sections": sections,
        "narrative": narrative,
        "follow_up_questions": questions,
        "peer": {
            "key": peer_key,
            "p90": None if pd.isna(peer_p90) else float(peer_p90),
            "cost_zscore": None if pd.isna(cost_zscore) else float(cost_zscore),
        },
        "claim": {
            "dx_primary_code": row.get("dx_primary_code"),
            "dx_primary_label": dx_label,
            "severity_group": severity,
            "service_type": service_type,
            "facility_class": facility_class,
            "province_name": province,
            "los": los,
            "amount_claimed": None if pd.isna(amount_claimed) else float(amount_claimed),
            "amount_paid": None if pd.isna(amount_paid) else float(amount_paid),
            "amount_gap": None if pd.isna(amount_gap) else float(amount_gap),
        },
        "latest_feedback": latest_feedback.to_dict() if latest_feedback else None,
    }


def _ensure_claim_exists(claim_id: str) -> None:
    loader = DataLoader()
    df = loader.load_claims_normalized(filters={"claim_id": claim_id})
    if df.empty:
        raise ClaimNotFound(f"Claim {claim_id} tidak ditemukan.")


def record_feedback(claim_id: str, reviewer: User, payload: dict[str, Any]) -> AuditOutcome:
    """Persist auditor feedback for a claim and return the stored record."""
    _ensure_claim_exists(claim_id)

    decision = (payload.get("decision") or "").strip().lower()
    if decision not in ALLOWED_DECISIONS:
        raise FeedbackValidationError(f"Nilai decision harus salah satu dari {sorted(ALLOWED_DECISIONS)}")

    correction_ratio_raw = payload.get("correction_ratio")
    correction_ratio = None
    if correction_ratio_raw is not None:
        try:
            correction_ratio = float(correction_ratio_raw)
        except (TypeError, ValueError) as exc:
            raise FeedbackValidationError("correction_ratio harus berupa angka 0-1") from exc
        if not 0 <= correction_ratio <= 1:
            raise FeedbackValidationError("correction_ratio harus berada pada rentang 0-1")

    notes = payload.get("notes")

    outcome = AuditOutcome(
        claim_id=claim_id,
        decision=decision,
        correction_ratio=correction_ratio,
        notes=notes,
        reviewer_id=reviewer.id if reviewer else None,
    )

    db.session.add(outcome)
    db.session.commit()
    return outcome
