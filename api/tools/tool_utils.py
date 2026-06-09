from __future__ import annotations

from datetime import date
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "models" / "house_price_lgbm_pipeline.joblib"
METRICS_PATH = MODEL_PATH.with_suffix(".metrics.json")
TRAIN_DATASET_PATH = ROOT / "data" / "train" / "train.csv"
DATE_ORIGIN = date(2000, 1, 1)
NON_MODEL_COLUMNS = {"price", "address", "maxDistanceKm", "sqftTolerancePct", "yearTolerance"}
CONFIDENCE_LEVELS = ("high", "medium", "low")


def parse_float(value: Any, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def format_currency(value: float | None) -> str:
    if value is None or np.isnan(value):
        return "n/a"
    return f"${value:,.0f}"


def format_number(value: float | None, digits: int = 1) -> str:
    if value is None or np.isnan(value):
        return "n/a"
    if digits == 0:
        return f"{value:,.0f}"
    return f"{value:,.{digits}f}"


def format_feature_value(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        return format_number(float(value), digits=2)
    return str(value)


def haversine_km(
    lat1: float | None,
    lon1: float | None,
    lat2: float | None,
    lon2: float | None,
) -> float | None:
    if None in {lat1, lon1, lat2, lon2}:
        return None

    lat1_r, lon1_r, lat2_r, lon2_r = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = sin(dlat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return 6371.0 * c
