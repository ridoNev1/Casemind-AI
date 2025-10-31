def get_severity_mismatch() -> list[dict[str, float | str]]:
    """Mock severity mismatch output mimicking recipe columns."""
    return [
        {
            "claim_id": "CLAIM-DEMO-002",
            "dx_primary": "B509",
            "facility_class": "C",
            "province": "Papua",
            "los": 0,
            "claimed": 2250000.0,
            "peer_p90": 1600000.0,
            "delta_pct": 40.6,
        }
    ]


def get_duplicate_claims() -> list[dict[str, str]]:
    """Mock duplicate claim view."""
    return [
        {
            "claim_id": "CLAIM-DEMO-003",
            "matched_claim_id": "CLAIM-DEMO-004",
            "dx_primary": "O80",
            "procedure_code": "9059",
            "episode_gap_days": 2,
        }
    ]
