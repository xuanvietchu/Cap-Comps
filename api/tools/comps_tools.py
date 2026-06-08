from datetime import datetime
import pandas as pd
import numpy as np
from langchain.tools import tool

from api.data import df


def haversine_km(lat1, lon1, lat2, lon2):
    """
    Distance between two lat/lon points in kilometers.
    """
    R = 6371

    lat1, lon1, lat2, lon2 = map(
        np.radians,
        [lat1, lon1, lat2, lon2]
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    )

    return 2 * R * np.arcsin(np.sqrt(a))


@tool
def get_matches_by_period(
    address: str,
    start_date: str,
    end_date: str = datetime.now().strftime("%Y-%m-%d"),
    top_k: int = 15,
    max_distance_km: float = 3.0,
    sqft_tolerance_pct: float = 0.20,
    year_tolerance: int = 10,
):
    """
    Return house comps for one address inside a sold-date period.

    Default comp filters:
    - within 3 km
    - within 20% living area
    - within 10 years of age/year built

    User may change:
    - max_distance_km
    - sqft_tolerance_pct
    - year_tolerance

    start_date and end_date must be YYYY-MM-DD.
    """

    reference_date = pd.Timestamp("2000-01-01", tz="UTC")

    start_days = (pd.to_datetime(start_date, utc=True) - reference_date).days
    end_days = (pd.to_datetime(end_date, utc=True) - reference_date).days

    # Find target property
    target_matches = df[
        df["address"].str.lower().str.strip()
        == address.lower().strip()
    ]

    if target_matches.empty:
        return {
            "error": f"No property found for address: {address}"
        }

    target = target_matches.iloc[0]

    target_lat = target["lat"]
    target_lon = target["lon"]
    target_sqft = target["livingArea"]
    target_year = target["yearBuiltActual"]

    period_df = df[
        (df["closeDate_days"] >= start_days)
        & (df["closeDate_days"] <= end_days)
    ].copy()

    # Remove target property itself if present
    period_df = period_df[
        period_df["address"].str.lower().str.strip()
        != address.lower().strip()
    ]

    # Distance filter
    period_df["distance_km"] = haversine_km(
        target_lat,
        target_lon,
        period_df["lat"],
        period_df["lon"],
    )

    period_df = period_df[
        period_df["distance_km"] <= max_distance_km
    ]

    # Square footage filter
    sqft_min = target_sqft * (1 - sqft_tolerance_pct)
    sqft_max = target_sqft * (1 + sqft_tolerance_pct)

    period_df = period_df[
        (period_df["livingArea"] >= sqft_min)
        & (period_df["livingArea"] <= sqft_max)
    ]

    # Age/year-built filter
    period_df = period_df[
        period_df["yearBuiltActual"].between(
            target_year - year_tolerance,
            target_year + year_tolerance
        )
    ]

    matches = (
        period_df
        .sort_values(
            ["closeDate_days", "distance_km"],
            ascending=[False, True]
        )
        .head(top_k)
    )

    return {
        "target_address": address,
        "date_range": {
            "start_date": start_date,
            "end_date": end_date,
        },
        "filters": {
            "max_distance_km": max_distance_km,
            "sqft_tolerance_pct": sqft_tolerance_pct,
            "year_tolerance": year_tolerance,
        },
        "matches": matches.to_dict(orient="records"),
    }