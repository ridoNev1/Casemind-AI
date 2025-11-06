"""Schema definitions and validators for analytics datasets."""

from __future__ import annotations

from typing import Iterable, Sequence

import pandas as pd


CLAIMS_NORMALIZED_REQUIRED_COLUMNS: tuple[str, ...] = (
    "claim_id",
    "admit_dt",
    "discharge_dt",
    "los",
    "province_code",
    "district_code",
    "facility_ownership_code",
    "facility_type_code",
    "facility_class_code",
    "service_level_code",
    "severity_code",
    "dx_primary_code",
    "dx_primary_label",
    "dx_primary_group",
    "amount_claimed",
    "amount_paid",
    "patient_key",
    "family_key",
    "province_name",
    "facility_class",
    "service_type",
    "severity_group",
    "dx_secondary_codes",
    "dx_secondary_labels",
    "peer_mean",
    "peer_p90",
    "cost_zscore",
)


def find_missing_columns(df: pd.DataFrame, required: Sequence[str]) -> list[str]:
    """Return list of columns missing from dataframe."""
    return [col for col in required if col not in df.columns]


def validate_claims_normalized(df: pd.DataFrame, required: Iterable[str] | None = None) -> None:
    """
    Validate that dataframe contains required columns for downstream consumption.

    Raises:
        ValueError: if required columns are missing.
    """
    to_check = tuple(required) if required is not None else CLAIMS_NORMALIZED_REQUIRED_COLUMNS
    missing = find_missing_columns(df, to_check)
    if missing:
        raise ValueError(f"claims_normalized missing columns: {missing}")
