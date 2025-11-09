from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "instance/analytics.duckdb")
SIM_LOG_PATH = Path(os.getenv("SIM_LOG_PATH", "instance/logs/simulation_runs.jsonl"))
DEFAULT_INTERVAL = float(os.getenv("SIM_INTERVAL_SECONDS", "10"))
DEFAULT_DURATION = int(os.getenv("SIM_DURATION_SECONDS", "300"))
DEFAULT_MAX = int(os.getenv("SIM_MAX_CLAIMS", "100"))
DEFAULT_JITTER = float(os.getenv("SIM_INTERVAL_JITTER", "0.3"))  # 30%
DEFAULT_FRAUD_RATIO = float(os.getenv("SIM_FRAUD_RATIO", "0.8"))
SIM_LLM_MODEL = os.getenv("SIM_LLM_MODEL", os.getenv("COPILOT_LLM_MODEL", "gpt-4o-mini"))
SIM_FORCE_LLM = os.getenv("SIM_FORCE_LLM", "true").lower() in {"1", "true", "yes"}
SIM_CLAIM_PREFIX = os.getenv("SIM_CLAIM_PREFIX", "SIM")

FRAUD_FLAG_CHOICES = [
    ["short_stay_high_cost"],
    ["short_stay_high_cost", "high_cost_full_paid"],
    ["duplicate_pattern"],
    ["duplicate_pattern", "short_stay_high_cost"],
]
NORMAL_FLAG_CHOICES = [
    [],
    ["duplicate_pattern"],
]

_LLM_CLIENT: OpenAI | None = None


def _connect() -> duckdb.DuckDBPyConnection:
    if not Path(DUCKDB_PATH).exists():
        raise FileNotFoundError(f"DuckDB path not found: {DUCKDB_PATH}")
    return duckdb.connect(DUCKDB_PATH)


def _ensure_table(con: duckdb.DuckDBPyConnection) -> list[str]:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS claims_live_stream AS
        SELECT * FROM claims_normalized LIMIT 0;
        """
    )
    columns = (
        con.execute("PRAGMA table_info('claims_live_stream')")
        .fetchdf()["name"]
        .tolist()
    )
    return columns


def _sample_base_row(con: duckdb.DuckDBPyConnection) -> pd.Series:
    df = con.execute(
        "SELECT * FROM claims_normalized USING SAMPLE reservoir(1 ROWS);"
    ).fetchdf()
    if df.empty:
        raise RuntimeError("claims_normalized table is empty; cannot generate sample.")
    return df.iloc[0]


def _get_llm_client() -> OpenAI | None:
    global _LLM_CLIENT
    if _LLM_CLIENT is not None:
        return _LLM_CLIENT
    api_key = os.getenv("OPEN_AI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return None
    _LLM_CLIENT = OpenAI(api_key=api_key)
    return _LLM_CLIENT


def _summarize_row(row: pd.Series) -> dict[str, Any]:
    return {
        "dx_primary_code": row.get("dx_primary_code"),
        "dx_primary_label": row.get("dx_primary_label"),
        "severity_group": row.get("severity_group"),
        "service_type": row.get("service_type"),
        "facility_name": row.get("facility_name"),
        "facility_class": row.get("facility_class"),
        "province_name": row.get("province_name"),
        "los": row.get("los"),
        "amount_claimed": row.get("amount_claimed"),
        "amount_paid": row.get("amount_paid"),
        "bpjs_payment_ratio": row.get("bpjs_payment_ratio"),
        "risk_score": row.get("risk_score"),
        "flags": row.get("flags"),
    }


def _collect_response_text(completion: Any) -> str | None:
    text = getattr(completion, "output_text", None)
    if text:
        return text
    chunks: list[str] = []
    for item in getattr(completion, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            txt = getattr(content, "text", None)
            if txt and hasattr(txt, "value"):
                chunks.append(txt.value)
    return "".join(chunks) if chunks else None


def _extract_json_dict(text: str | None) -> dict[str, Any] | None:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*", "", cleaned).strip("` \n")
    match = re.search(r"\{.*\}", cleaned, flags=re.S)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _llm_generate_claim(row: pd.Series, is_fraud: bool) -> dict[str, Any]:
    client = _get_llm_client()
    if client is None:
        return {}
    payload = {
        "base_claim": _summarize_row(row),
        "fraudulent": is_fraud,
        "target_fields": [
            "dx_primary_code",
            "dx_primary_label",
            "severity_group",
            "service_type",
            "facility_name",
            "facility_class",
            "province_name",
            "los",
            "amount_claimed",
            "amount_paid",
            "bpjs_payment_ratio",
            "flags",
            "notes",
        ],
    }
    fraud_hint = "fraudulent / high-risk" if is_fraud else "legitimate / normal"
    system_prompt = (
        "Anda adalah generator klaim BPJS sintetis. "
        "Selalu keluarkan JSON valid dan gunakan nilai realistis (rupiah, LOS >= 1). "
        "Jika diminta klaim fraudulent, tonjolkan pola biaya tinggi LOS singkat dan flag relevan."
    )
    user_prompt = (
        "Buat klaim {fraud_hint}. Ambil konteks dari data berikut namun ubah jika perlu. "
        "Output wajib JSON dengan keys: "
        "dx_primary_code, dx_primary_label, severity_group, service_type, "
        "facility_name, facility_class, province_name, los, amount_claimed, amount_paid, "
        "bpjs_payment_ratio, flags (array), dx_secondary_codes, dx_secondary_labels, narrative.\n"
        "Pastikan amount_paid <= amount_claimed dan bpjs_payment_ratio = amount_paid / amount_claimed."
    ).format(fraud_hint=fraud_hint)
    try:
        completion = client.responses.create(
            model=SIM_LLM_MODEL,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{user_prompt}\nData: {json.dumps(payload, default=str)}"},
            ],
            temperature=0.55 if is_fraud else 0.35,
            max_output_tokens=600,
        )
        text = _collect_response_text(completion)
        parsed = _extract_json_dict(text)
        return parsed or {}
    except Exception:
        return {}


def _generate_claim_id() -> str:
    return f"{SIM_CLAIM_PREFIX}-{uuid.uuid4().hex[:12].upper()}"


def _safe_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _safe_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _normalize_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",") if part.strip()]
        return parts
    return []


def _generate_timestamps(los: int) -> tuple[datetime, datetime, datetime]:
    los = max(1, los)
    generated_at = datetime.now(tz=timezone.utc)
    admit_dt = generated_at - timedelta(hours=random.randint(1, 48))
    discharge_dt = admit_dt + timedelta(days=los)
    return admit_dt, discharge_dt, generated_at


def _assign_flags(is_fraud: bool, incoming: list[Any]) -> list[str]:
    if incoming:
        normalized = [str(item) for item in incoming if item]
        if normalized:
            return normalized
    choice_pool = FRAUD_FLAG_CHOICES if is_fraud else NORMAL_FLAG_CHOICES
    return random.choice(choice_pool).copy()


def _apply_scores(payload: dict[str, Any], is_fraud: bool) -> None:
    if is_fraud:
        risk_score = round(random.uniform(0.75, 0.99), 4)
        rule_score = round(random.uniform(0.6, min(0.95, risk_score + 0.05)), 4)
        ml_score = round(random.uniform(0.015, 0.12), 6)
    else:
        risk_score = round(random.uniform(0.2, 0.55), 4)
        rule_score = round(random.uniform(0.0, min(0.4, risk_score)), 4)
        ml_score = round(random.uniform(-0.08, 0.04), 6)
    ml_score_normalized = max(0.0, min(1.0, 0.5 + ml_score))
    payload["risk_score"] = risk_score
    payload["rule_score"] = rule_score
    payload["ml_score"] = ml_score
    payload["ml_score_normalized"] = ml_score_normalized
    payload["duplicate_pattern"] = "duplicate_pattern" in (payload.get("flags") or [])


def _apply_llm_payload(row: pd.Series, llm_data: dict[str, Any], claim_id: str, is_fraud: bool) -> dict[str, Any]:
    los = _safe_int(llm_data.get("los"), int(row.get("los") or 1))
    admit_dt, discharge_dt, generated_at = _generate_timestamps(los)
    amount_claimed = _safe_float(llm_data.get("amount_claimed"), float(row.get("amount_claimed") or 0) or 1_000_000)
    amount_paid = _safe_float(llm_data.get("amount_paid"), float(row.get("amount_paid") or 0))
    amount_paid = min(amount_claimed, amount_paid if amount_paid > 0 else amount_claimed * (0.95 if is_fraud else 0.75))
    bpjs_ratio = llm_data.get("bpjs_payment_ratio")
    if isinstance(bpjs_ratio, (int, float)):
        bpjs_payment_ratio = float(bpjs_ratio)
    else:
        bpjs_payment_ratio = 0 if amount_claimed == 0 else round(amount_paid / amount_claimed, 4)
    payload = row.to_dict()
    payload.update(
        {
            "claim_id": llm_data.get("claim_id") or claim_id,
            "admit_dt": admit_dt,
            "discharge_dt": discharge_dt,
            "generated_at": generated_at,
            "los": max(1, los),
            "dx_primary_code": llm_data.get("dx_primary_code") or row.get("dx_primary_code"),
            "dx_primary_label": llm_data.get("dx_primary_label") or row.get("dx_primary_label"),
            "severity_group": llm_data.get("severity_group") or row.get("severity_group"),
            "service_type": llm_data.get("service_type") or row.get("service_type"),
            "facility_name": llm_data.get("facility_name") or row.get("facility_name"),
            "facility_class": llm_data.get("facility_class") or row.get("facility_class"),
            "province_name": llm_data.get("province_name") or row.get("province_name"),
            "amount_claimed": round(amount_claimed, 2),
            "amount_paid": round(amount_paid, 2),
            "amount_gap": round(amount_claimed - amount_paid, 2),
            "bpjs_payment_ratio": round(bpjs_payment_ratio, 4),
            "dx_secondary_codes": _normalize_list(llm_data.get("dx_secondary_codes")) or row.get("dx_secondary_codes"),
            "dx_secondary_labels": _normalize_list(llm_data.get("dx_secondary_labels")) or row.get("dx_secondary_labels"),
            "narrative": llm_data.get("narrative"),
        }
    )
    payload["flags"] = _assign_flags(is_fraud, _normalize_list(llm_data.get("flags")))
    _apply_scores(payload, is_fraud)
    return payload


def _fallback_mutation(row: pd.Series, claim_id: str, is_fraud: bool) -> dict[str, Any]:
    los = int(row.get("los") or 1)
    admit_dt, discharge_dt, generated_at = _generate_timestamps(los)
    amount_claimed = float(row.get("amount_claimed") or random.uniform(1_000_000, 6_000_000))
    factor = random.uniform(1.2, 1.8) if is_fraud else random.uniform(0.85, 1.1)
    amount_claimed = round(amount_claimed * factor, 2)
    amount_paid_factor = random.uniform(0.92, 1.0) if is_fraud else random.uniform(0.6, 1.0)
    amount_paid = min(amount_claimed, round(amount_claimed * amount_paid_factor, 2))
    payload = row.to_dict()
    payload.update(
        {
            "claim_id": claim_id,
            "admit_dt": admit_dt,
            "discharge_dt": discharge_dt,
            "generated_at": generated_at,
            "los": max(1, los),
            "amount_claimed": amount_claimed,
            "amount_paid": amount_paid,
            "amount_gap": amount_claimed - amount_paid,
            "bpjs_payment_ratio": round(amount_paid / amount_claimed, 4) if amount_claimed else 0.0,
        }
    )
    payload["flags"] = _assign_flags(is_fraud, payload.get("flags") or [])
    _apply_scores(payload, is_fraud)
    return payload


def _mutate_row(row: pd.Series, is_fraud: bool) -> dict[str, Any]:
    claim_id = _generate_claim_id()
    llm_payload = _llm_generate_claim(row, is_fraud)
    if llm_payload:
        return _apply_llm_payload(row, llm_payload, claim_id, is_fraud)
    if SIM_FORCE_LLM:
        raise RuntimeError(
            "SIM_FORCE_LLM=true tetapi LLM tidak menghasilkan output. "
            "Pastikan OPENAI_API_KEY terpasang atau set SIM_FORCE_LLM=false."
        )
    return _fallback_mutation(row, claim_id, is_fraud)


def _insert_claim(con: duckdb.DuckDBPyConnection, columns: list[str], payload: dict[str, Any]) -> None:
    df = pd.DataFrame([payload], columns=columns)
    con.register("sim_df", df)
    con.execute("INSERT INTO claims_live_stream SELECT * FROM sim_df")
    con.unregister("sim_df")


def _log_run(run_info: dict[str, Any]) -> None:
    SIM_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SIM_LOG_PATH.open("a") as fp:
        fp.write(json.dumps(run_info, default=str))
        fp.write("\n")


def run_simulation(duration: int, interval: float, max_claims: int, jitter: float, fraud_ratio: float) -> dict[str, Any]:
    start_time = datetime.now(tz=timezone.utc)
    inserted = 0
    fraud_inserted = 0
    with _connect() as con:
        columns = _ensure_table(con)
        end_time = time.monotonic() + duration
        while inserted < max_claims and time.monotonic() < end_time:
            base_row = _sample_base_row(con)
            is_fraud = random.random() < fraud_ratio
            payload = _mutate_row(base_row, is_fraud=is_fraud)
            _insert_claim(con, columns, payload)
            inserted += 1
            if is_fraud:
                fraud_inserted += 1

            sleep_seconds = interval * random.uniform(1 - jitter, 1 + jitter)
            time.sleep(max(sleep_seconds, 0.1))

    end_time_dt = datetime.now(tz=timezone.utc)
    run_info = {
        "started_at": start_time,
        "ended_at": end_time_dt,
        "duration_seconds": (end_time_dt - start_time).total_seconds(),
        "inserted_claims": inserted,
        "fraudulent_claims": fraud_inserted,
        "fraud_ratio_target": fraud_ratio,
        "duckdb_path": DUCKDB_PATH,
        "llm_model": SIM_LLM_MODEL if _LLM_CLIENT else None,
        "force_llm": SIM_FORCE_LLM,
    }
    _log_run(run_info)
    return run_info


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run synthetic claim generator.")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION, help="Durasi simulasi dalam detik.")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="Interval dasar antar klaim (detik).")
    parser.add_argument("--max-claims", type=int, default=DEFAULT_MAX, help="Jumlah klaim maksimum yang akan dibuat.")
    parser.add_argument("--jitter", type=float, default=DEFAULT_JITTER, help="Persentase jitter (0-1).")
    parser.add_argument("--fraud-ratio", type=float, default=DEFAULT_FRAUD_RATIO, help="Peluang klaim diset sebagai 'fraudulent' (0-1).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    info = run_simulation(
        duration=args.duration,
        interval=args.interval,
        max_claims=args.max_claims,
        jitter=args.jitter,
        fraud_ratio=args.fraud_ratio,
    )
    print(
        f"Simulation completed. Inserted {info['inserted_claims']} claims in "
        f"{info['duration_seconds']:.1f}s (DuckDB: {info['duckdb_path']})."
    )


if __name__ == "__main__":
    main()
