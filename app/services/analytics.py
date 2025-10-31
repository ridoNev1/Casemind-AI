def get_casemix_by_province() -> list[dict[str, float | int | str]]:
    """Mock casemix metrics grouped by province."""
    return [
        {
            "province": "Papua",
            "claim_count": 1200,
            "avg_los": 1.4,
            "median_claim_to_paid_ratio": 1.12,
            "high_risk_rate": 0.07,
        }
    ]
