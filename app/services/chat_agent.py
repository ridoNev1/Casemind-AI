from __future__ import annotations

from typing import Any, Iterable, List

from flask import current_app
import pandas as pd

from . import audit_copilot
from .audit_copilot import FLAG_DESCRIPTIONS
from .chat_history import list_chat_messages
from . import risk_scoring
from ml.common.data_access import DataLoader
from . import reports

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
    from langchain_core.tools import tool
except ImportError:  # pragma: no cover - optional dependency
    ChatOpenAI = None
    AIMessage = HumanMessage = SystemMessage = ToolMessage = None


def _describe_risk(score: float | None) -> str:
    if score is None:
        return "tidak tersedia"
    if score >= 0.9:
        return "kategori sangat tinggi – wajib audit menyeluruh"
    if score >= 0.75:
        return "kategori tinggi – prioritaskan untuk audit"
    if score >= 0.5:
        return "kategori sedang – perlu pemeriksaan lanjutan"
    return "kategori rendah – cukup dipantau"


def _build_context_text(row: pd.Series) -> str:
    ident = row.get("dx_primary_label") or row.get("dx_primary_code") or "-"
    facility_class = row.get("facility_class") or "-"
    province = row.get("province_name") or "-"
    severity = row.get("severity_group") or "-"
    service_type = row.get("service_type") or "-"
    los = row.get("los")
    los_text = f"LOS {int(los)} hari" if pd.notna(los) else "LOS tidak tercatat"

    amount_claimed = audit_copilot._format_currency(row.get("amount_claimed"))  # type: ignore[attr-defined]
    amount_paid = audit_copilot._format_currency(row.get("amount_paid"))  # type: ignore[attr-defined]
    amount_gap = audit_copilot._format_currency(row.get("amount_gap"))  # type: ignore[attr-defined]

    peer_key = row.get("peer_key") or "-"
    peer_p90 = audit_copilot._format_currency(row.get("peer_p90"))  # type: ignore[attr-defined]
    cost_zscore = row.get("cost_zscore")
    peer_text = (
        f"P90 {peer_p90} dengan z-score {cost_zscore:.2f}" if peer_p90 and pd.notna(cost_zscore) else "statistik peer tidak lengkap"
    )

    risk_score = row.get("risk_score")
    risk_desc = _describe_risk(risk_score)
    risk_score_or_zero = risk_score if risk_score is not None else 0
    rule_score = row.get("rule_score")
    ml_score = row.get("ml_score_normalized")
    flags = audit_copilot._hydrate_flags(row)  # type: ignore[attr-defined]
    flag_desc = "; ".join(FLAG_DESCRIPTIONS.get(flag, flag) for flag in flags) or "Tidak ada flag rules aktif."

    return (
        f"Diagnosa {ident} (severity {severity}, layanan {service_type}) di {facility_class} – {province}; {los_text}. "
        f"Biaya klaim {amount_claimed}, dibayar {amount_paid}, gap {amount_gap}. Peer {peer_key}: {peer_text}. "
        f"Skor risiko {risk_score_or_zero:.2f} ({risk_desc}; rule_score={rule_score}, ml_score_normalized={ml_score}). "
        f"Flag: {flag_desc}."
    )


@tool
def peer_detail_tool(claim_id: str) -> str:
    """Ambil statistik peer (mean/p90/z-score) untuk klaim tertentu."""
    try:
        loader = DataLoader()
        df = loader.load_claims_normalized(filters={"claim_id": claim_id})
    except Exception as exc:  # pragma: no cover - data failure
        return f"Gagal mengambil data peer: {exc}"
    if df.empty:
        return "Tidak menemukan data peer untuk claim tersebut."
    row = df.iloc[0]
    peer_key = row.get("peer_key") or "-"
    def _to_float(val):
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    mean = _to_float(row.get("peer_mean"))
    p90 = _to_float(row.get("peer_p90"))
    z = _to_float(row.get("cost_zscore"))
    province = row.get("province_name") or "-"
    facility = row.get("facility_class") or "-"
    return (
        f"Peer {peer_key} ({facility}, {province}) memiliki mean Rp {mean:,.0f} dan P90 Rp {p90:,.0f} "
        f"dengan z-score {z:.2f}."
        if mean and p90 and pd.notna(z)
        else f"Peer {peer_key} untuk klaim ini belum memiliki statistik lengkap."
    )


@tool
def flag_explainer_tool(claim_id: str) -> str:
    """Jelaskan flag rules aktif + statistik pendek untuk claim tertentu."""
    loader = DataLoader()
    df = loader.load_claims_normalized(filters={"claim_id": claim_id})
    if df.empty:
        return "Tidak menemukan klaim untuk menjelaskan flag."
    row = df.iloc[0]
    flags = risk_scoring._compute_flag_columns(row.to_frame().T)["flags"].iloc[0]  # type: ignore[attr-defined]
    flags = flags or []
    if not flags:
        return "Klaim ini tidak memiliki flag rules aktif."
    explanations = []
    for flag in flags:
        desc = FLAG_DESCRIPTIONS.get(flag, flag.replace("_", " "))
        count_df = loader.query(
            f"SELECT COUNT(*) AS cnt FROM {risk_scoring.SCORES_CACHE_TABLE} WHERE ARRAY_CONTAINS(flags, ?)",
            params=[flag],
        )
        cnt = int(count_df["cnt"].iloc[0]) if not count_df.empty else 0
        explanations.append(f"{flag}: {desc} (terjadi pada {cnt} klaim)")
    return "; ".join(explanations)


@tool
def tariff_insight_tool(claim_id: str) -> str:
    """Berikan ringkasan gap tarif fasilitas/dx terkait klaim."""
    loader = DataLoader()
    df = loader.load_claims_normalized(filters={"claim_id": claim_id})
    if df.empty:
        return "Klaim tidak ditemukan untuk analisis tarif."
    row = df.iloc[0]
    facility_id = row.get("facility_id")
    province = row.get("province_name")
    dx_group = row.get("dx_primary_group")
    def _fetch(limit: int, use_facility: bool = True, use_province: bool = True, use_dx: bool = True):
        return reports.get_tariff_insight(
            limit=limit,
            facility_id=facility_id if use_facility and pd.notna(facility_id) else None,
            province=province if use_province and pd.notna(province) else None,
            dx_group=dx_group if use_dx and pd.notna(dx_group) else None,
        )

    records = _fetch(limit=3, use_facility=True, use_province=True, use_dx=True)
    fallback_note = ""
    if not records:
        records = _fetch(limit=3, use_facility=False, use_province=True, use_dx=True)
        fallback_note = " (menggunakan agregasi provinsi+dx karena data fasilitas spesifik tidak tersedia)"
    if not records:
        records = _fetch(limit=3, use_facility=False, use_province=True, use_dx=False)
        fallback_note = " (menggunakan agregasi provinsi karena data fasilitas/dx khusus tidak tersedia)"
    if not records:
        records = _fetch(limit=3, use_facility=False, use_province=False, use_dx=False)
        fallback_note = " (menggunakan agregasi nasional karena data granular tidak tersedia)"
    if not records:
        return "Tidak ada data tarif agregat sama sekali untuk referensi klaim ini."
    lines = []
    for rec in records:
        lines.append(
            f"{rec['facility_name']} ({rec['province_name']}) – dx_group {rec['dx_primary_group']}: gap total Rp {rec['total_gap']:,.0f} "
            f"dengan rata-rata gap Rp {rec['avg_gap']:,.0f}."
        )
    return " ; ".join(lines) + fallback_note


def _build_llm():
    if ChatOpenAI is None:
        return None
    cfg = audit_copilot._get_llm_config()  # type: ignore[attr-defined]
    if not cfg:
        return None
    llm = ChatOpenAI(
        api_key=cfg["api_key"],
        model=cfg["model"],
        temperature=cfg.get("temperature", 0.2),
        max_tokens=cfg.get("max_tokens", 400),
    )
    return llm.bind_tools([peer_detail_tool, flag_explainer_tool, tariff_insight_tool])


def generate_chat_reply(
    claim_id: str,
    user_message: str,
    history: list[dict[str, Any]] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Generate LLM-based reply with claim context + history."""
    context = audit_copilot._load_claim_context(claim_id)  # type: ignore[attr-defined]
    row = context.data
    context_text = _build_context_text(row)
    history = history or list_chat_messages(claim_id)
    risk_score_val = row.get("risk_score") if pd.notna(row.get("risk_score")) else None
    risk_desc = _describe_risk(risk_score_val)
    risk_score_fmt = f"{float(risk_score_val):.2f}" if risk_score_val is not None else "n/a"
    cost_z = row.get("cost_zscore")
    cost_z_fmt = f"{float(cost_z):.2f}" if cost_z is not None and not pd.isna(cost_z) else "n/a"

    llm = _build_llm()
    if llm is None:
        fallback = (
            f"Saat ini layanan LLM tidak aktif. Namun berdasarkan data: {context_text} "
            f"Pertanyaan kamu: '{user_message}'. Gunakan informasi di atas untuk memutuskan tindak lanjut."
        )
        return fallback, {"provider": None, "model": None, "cached": False}

    system_prompt = (
        "Anda adalah Audit Copilot untuk klaim BPJS. Jawab ringkas (maks 4 kalimat) dengan bahasa yang mudah dipahami auditor, "
        "hindari menyebut istilah teknis mentah (mis. risk_score) tanpa menjelaskan maknanya dalam kata-kata. "
        "Sampaikan alasan risiko berbasis data (biaya, peer, flag) dan tutup dengan saran tindakan. "
        "Jika pertanyaan di luar konteks klaim, arahkan kembali ke data klaim."
    )
    messages: List[Any] = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Konteks klaim: {context_text}"),
    ]
    lower_msg = user_message.lower()
    keyword_contexts: list[str] = []
    appended_info: list[str] = []
    if "tarif" in lower_msg or "tariff" in lower_msg:
        appended_info.append(f"Tarif insight: {tariff_insight_tool.invoke({'claim_id': claim_id})}")
        appended_info.append(
            f"Catatan risiko tarif: walaupun gap tarif bisa nol, klaim ini memiliki skor risiko {risk_score_fmt} ({risk_desc}) dan cost_zscore {cost_z_fmt}."
        )
    if "peer" in lower_msg or "p90" in lower_msg:
        appended_info.append(f"Peer detail: {peer_detail_tool.invoke({'claim_id': claim_id})}")
    if "flag" in lower_msg:
        appended_info.append(f"Flag detail: {flag_explainer_tool.invoke({'claim_id': claim_id})}")
    if appended_info:
        user_message = f"{user_message}\n\nData pendukung:\n- " + "\n- ".join(appended_info)
    for record in history:
        content = record.get("content", "")
        if not content:
            continue
        role = record.get("role", "user")
        if role == "assistant":
            messages.append(AIMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))

    if not history or history[-1].get("content") != user_message or history[-1].get("role") != "user":
        messages.append(HumanMessage(content=user_message))

    completion = llm.invoke(messages)
    # handle tool calls (single iteration sufficient for simple tool use)
    if getattr(completion, "tool_calls", None):
        tool_messages: List[Any] = []
        for call in completion.tool_calls:
            name = call.get("name")
            args = call.get("args") or {}
            result = ""
            claim_arg = args.get("claim_id") or claim_id
            if name == "peer_detail_tool":
                result = peer_detail_tool.invoke({"claim_id": claim_arg})
            elif name == "flag_explainer_tool":
                result = flag_explainer_tool.invoke({"claim_id": claim_arg})
            elif name == "tariff_insight_tool":
                result = tariff_insight_tool.invoke({"claim_id": claim_arg})
            tool_messages.append(
                ToolMessage(content=result, tool_call_id=call.get("id"))
            )
        messages.extend([completion, *tool_messages])
        completion = llm.invoke(messages)

    reply_text = completion.content if isinstance(completion.content, str) else str(completion.content)
    metadata = {
        "provider": "openai",
        "model": llm.model_name,
        "cached": False,
    }
    return reply_text.strip(), metadata
