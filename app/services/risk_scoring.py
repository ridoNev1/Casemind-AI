from collections.abc import Mapping
from typing import Any


def get_high_risk_claims(filters: Mapping[str, Any]) -> list[dict[str, Any]]:
    """
    Placeholder implementation returning mock data.

    Real version will query analytics store (DuckDB) and apply rules from
    data-recipes/ml-recipes documents.
    """
    province = filters.get("province") or "ALL"
    dx_code = filters.get("dx") or "B999"
    return [
        {
            "claim_id": "CLAIM-DEMO-001",
            "province": province,
            "dx_code": dx_code,
            "risk_score": 0.92,
            "flags": ["short_stay_high_cost", "high_cost_full_paid"],
            "peer": {"p90": 1600000, "z": 2.7},
        }
    ]
