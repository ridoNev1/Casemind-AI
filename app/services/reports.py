from __future__ import annotations

import math
from typing import Any

from ml.common.data_access import DataLoader


def get_severity_mismatch(limit: int = 200) -> list[dict[str, Any]]:
    """Return severity mismatch claims (severity ringan with costs above peer P90)."""
    loader = DataLoader()
    sql = """
        SELECT
            claim_id,
            dx_primary_code AS dx_primary,
            facility_class,
            COALESCE(province_name, 'UNKNOWN') AS province,
            los,
            amount_claimed AS claimed,
            peer_p90,
            CASE
                WHEN peer_p90 IS NULL OR peer_p90 = 0 THEN NULL
                ELSE (amount_claimed - peer_p90) / peer_p90 * 100
            END AS delta_pct
        FROM claims_normalized
        WHERE severity_group = 'ringan'
          AND amount_claimed IS NOT NULL
          AND peer_p90 IS NOT NULL
          AND peer_p90 > 0
          AND amount_claimed > peer_p90
        ORDER BY delta_pct DESC NULLS LAST
        LIMIT ?
    """
    df = loader.query(sql, params=[limit])
    if not df.empty:
        df = df.assign(delta_pct=df["delta_pct"].round(1))
    return df.to_dict(orient="records")


def get_duplicate_claims(limit: int = 200) -> list[dict[str, Any]]:
    """Return potential duplicate claims (<=3 day gap, same patient + dx/procedure)."""
    loader = DataLoader()
    sql = """
        WITH candidate_pairs AS (
            SELECT
                LEAST(a.claim_id, b.claim_id) AS claim_id_a,
                GREATEST(a.claim_id, b.claim_id) AS claim_id_b,
                a.dx_primary_code,
                a.procedure_code,
                ABS(DATE_DIFF('day', a.admit_dt, b.admit_dt)) AS episode_gap_days
            FROM claims_normalized a
            JOIN claims_normalized b
              ON a.patient_key = b.patient_key
             AND a.claim_id < b.claim_id
             AND COALESCE(a.dx_primary_code, '') = COALESCE(b.dx_primary_code, '')
             AND COALESCE(a.procedure_code, '') = COALESCE(b.procedure_code, '')
             AND a.patient_key IS NOT NULL
             AND ABS(DATE_DIFF('day', a.admit_dt, b.admit_dt)) <= 3
        )
        SELECT
            claim_id_a AS claim_id,
            claim_id_b AS matched_claim_id,
            dx_primary_code AS dx_primary,
            procedure_code,
            episode_gap_days
        FROM candidate_pairs
        ORDER BY episode_gap_days ASC, claim_id_a
        LIMIT ?
    """
    df = loader.query(sql, params=[limit])
    return df.to_dict(orient="records")


def get_tariff_insight(
    *,
    limit: int = 100,
    province: str | None = None,
    facility_id: str | None = None,
    severity: str | None = None,
    service_type: str | None = None,
    dx_group: str | None = None,
) -> list[dict[str, Any]]:
    """
    Aggregate tariff gap insight per facility + casemix.

    Returns rows sorted by total gap (claimed - paid) descending.
    """
    loader = DataLoader()

    where_clauses: list[str] = []
    params: list[Any] = []

    if province:
        where_clauses.append("COALESCE(province_name, 'UNKNOWN') = ?")
        params.append(province.upper())

    if facility_id:
        where_clauses.append("facility_id = ?")
        params.append(facility_id)

    if severity:
        where_clauses.append("LOWER(severity_group) = ?")
        params.append(severity.lower())

    if service_type:
        where_clauses.append("UPPER(service_type) = ?")
        params.append(service_type.upper())

    if dx_group:
        where_clauses.append("dx_primary_group = ?")
        params.append(dx_group)

    where_sql = ""
    if where_clauses:
        where_sql = " AND " + " AND ".join(where_clauses)

    sql = f"""
        SELECT
            facility_id,
            COALESCE(
                facility_name,
                NULLIF(TRIM(SPLIT_PART(region_facility_names, ';', 1)), ''),
                'UNKNOWN'
            ) AS facility_name,
            COALESCE(facility_match_quality, 'unmatched') AS facility_match_quality,
            COALESCE(province_name, 'UNKNOWN') AS province_name,
            COALESCE(district_name, 'UNKNOWN') AS district_name,
            dx_primary_group,
            COUNT(*) AS claim_count,
            SUM(amount_claimed) AS total_claimed,
            SUM(amount_paid) AS total_paid,
            SUM(amount_claimed - amount_paid) AS total_gap,
            AVG(amount_claimed - amount_paid) AS avg_gap,
            AVG(cost_zscore) AS avg_cost_zscore,
            AVG(bpjs_payment_ratio) AS avg_payment_ratio
        FROM claims_normalized
        WHERE amount_claimed IS NOT NULL
          AND amount_paid IS NOT NULL
          {where_sql}
        GROUP BY 1, 2, 3, 4, 5, 6
        ORDER BY total_gap DESC
        LIMIT ?
    """

    params.append(limit)
    df = loader.query(sql, params=params)
    if df.empty:
        return []

    numeric_cols = [
        "total_claimed",
        "total_paid",
        "total_gap",
        "avg_gap",
        "avg_cost_zscore",
        "avg_payment_ratio",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].round(2)

    records = df.to_dict(orient="records")
    for row in records:
        for key, value in list(row.items()):
            if isinstance(value, float) and math.isnan(value):
                row[key] = None
    return records
