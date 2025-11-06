from __future__ import annotations

from typing import Any

from ml.common.data_access import DataLoader


def get_casemix_by_province(limit: int | None = None) -> list[dict[str, Any]]:
    """Aggregate casemix metrics per province using DuckDB analytics output."""
    loader = DataLoader()

    sql = """
        SELECT
            COALESCE(province_name, 'UNKNOWN') AS province,
            COUNT(*) AS claim_count,
            AVG(los) AS avg_los,
            MEDIAN(CASE WHEN amount_claimed > 0 THEN amount_paid / amount_claimed ELSE NULL END) AS median_claim_to_paid_ratio,
            AVG(
                CASE
                    WHEN short_stay_high_cost
                      OR high_cost_full_paid
                      OR COALESCE(duplicate_pattern, FALSE)
                    THEN 1 ELSE 0
                END
            ) AS high_risk_rate
        FROM claims_scored
        GROUP BY 1
        ORDER BY claim_count DESC
    """

    params: list[Any] = []
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)

    df = loader.query(sql, params=params)
    return df.to_dict(orient="records")
