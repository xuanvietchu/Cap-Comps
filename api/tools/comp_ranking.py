from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from api.tools.model_store import load_dataset, quantile_model, transform_for_model
from api.tools.price_tools import predict_house_price
from api.tools.tool_utils import DATE_ORIGIN, haversine_km, parse_float, safe_str


def infer_search_constraints(details: dict[str, Any]) -> dict[str, float]:
    return {
        "maxDistanceKm": parse_float(details.get("maxDistanceKm"), 3.0) or 3.0,
        "sqftTolerancePct": parse_float(details.get("sqftTolerancePct"), 25.0) or 25.0,
        "yearTolerance": parse_float(details.get("yearTolerance"), 10.0) or 10.0,
    }


def price_per_sqft_value(price: float | None, living_area: float | None) -> float | None:
    if price is None or living_area is None or living_area <= 0:
        return None
    return float(price / living_area)


def price_per_sqft_similarity(subject_ppsf: float | None, candidate_ppsf: float | None) -> float:
    if subject_ppsf is None or candidate_ppsf is None:
        return 0.5

    denom = max(abs(subject_ppsf), abs(candidate_ppsf), 1.0)
    delta = abs(subject_ppsf - candidate_ppsf) / denom
    return float(max(0.0, 1.0 - min(delta, 1.0)))


def leaf_similarity_score(subject_details: dict[str, Any], candidate_details: dict[str, Any]) -> dict[str, float]:
    subject_frame = transform_for_model(subject_details)
    candidate_frame = transform_for_model(candidate_details)
    booster = quantile_model().booster_

    subject_leaves = np.asarray(booster.predict(subject_frame, pred_leaf=True)).reshape(-1)
    candidate_leaves = np.asarray(booster.predict(candidate_frame, pred_leaf=True)).reshape(-1)

    if subject_leaves.size == 0 or candidate_leaves.size == 0:
        return {
            "leaf_similarity_score": 0.0,
            "leaf_matches": 0,
            "leaf_count": 0,
        }

    leaf_matches = int(np.sum(subject_leaves == candidate_leaves))
    leaf_count = int(min(subject_leaves.size, candidate_leaves.size))
    return {
        "leaf_similarity_score": float(leaf_matches / leaf_count) if leaf_count else 0.0,
        "leaf_matches": leaf_matches,
        "leaf_count": leaf_count,
    }


def candidate_pool(subject: dict[str, Any]) -> pd.DataFrame:
    df = load_dataset().copy()
    constraints = infer_search_constraints(subject)

    if "assessmentClass" in subject and subject["assessmentClass"]:
        df = df[df["assessmentClass"].astype(str) == str(subject["assessmentClass"])].copy()

    subject_living_area = parse_float(subject.get("livingArea"))
    subject_year_built = parse_float(subject.get("yearBuilt"))
    subject_lat = parse_float(subject.get("lat"))
    subject_lon = parse_float(subject.get("lon"))

    if subject_living_area is not None:
        lower = subject_living_area * (1 - constraints["sqftTolerancePct"] / 100)
        upper = subject_living_area * (1 + constraints["sqftTolerancePct"] / 100)
        df = df[df["livingArea"].between(lower, upper, inclusive="both")].copy()

    if subject_year_built is not None:
        df = df[
            df["yearBuilt"].between(
                subject_year_built - constraints["yearTolerance"],
                subject_year_built + constraints["yearTolerance"],
                inclusive="both",
            )
        ].copy()

    if subject_lat is not None and subject_lon is not None and {"lat", "lon"}.issubset(df.columns):
        distances = []
        for _, row in df.iterrows():
            distance = haversine_km(
                subject_lat,
                subject_lon,
                parse_float(row.get("lat")),
                parse_float(row.get("lon")),
            )
            distances.append(distance if distance is not None else np.inf)
        df = df.assign(distance_km=distances)
        df = df[df["distance_km"] <= constraints["maxDistanceKm"] * 1.5].copy()
    else:
        df = df.assign(distance_km=np.nan)

    return df[df["price"].notna() & (df["price"] > 0)].copy()


def summarize_comp(comp: dict[str, Any]) -> dict[str, Any]:
    year_built = comp.get("yearBuilt")
    try:
        year_built = int(year_built)
    except (TypeError, ValueError):
        year_built = None

    return {
        "address": comp["address"],
        "sold_price": comp["sold_price"],
        "sold_date": comp["sold_date"],
        "distance_km": comp["distance_km"],
        "similarity_score": comp["similarity_score"],
        "leaf_similarity_score": comp["leaf_similarity_score"],
        "price_per_sqft_similarity": comp["price_per_sqft_similarity"],
        "leaf_matches": comp["leaf_matches"],
        "leaf_count": comp["leaf_count"],
        "subject_price_per_sqft": comp["subject_price_per_sqft"],
        "candidate_price_per_sqft": comp["candidate_price_per_sqft"],
        "predicted_value": comp["predicted_value"],
        "yearBuilt": year_built,
    }


def score_candidate(
    subject: dict[str, Any],
    candidate_row: dict[str, Any],
    subject_price: float | None,
    subject_ppsf: float | None,
) -> dict[str, Any]:
    leaf_similarity = leaf_similarity_score(subject, candidate_row)
    distance_km = parse_float(candidate_row.get("distance_km"))
    sold_date = None
    candidate_price = parse_float(candidate_row.get("price"))
    candidate_living_area = parse_float(candidate_row.get("livingArea"))
    candidate_year_built = parse_float(candidate_row.get("yearBuilt"))
    candidate_ppsf = price_per_sqft_value(candidate_price, candidate_living_area)
    ppsf_similarity = price_per_sqft_similarity(subject_ppsf, candidate_ppsf)
    combined_similarity = 0.5 * leaf_similarity["leaf_similarity_score"] + 0.5 * ppsf_similarity

    if "closeDate_days" in candidate_row and pd.notna(candidate_row["closeDate_days"]):
        try:
            sold_date = DATE_ORIGIN + timedelta(days=int(float(candidate_row["closeDate_days"])))
        except (TypeError, ValueError, OverflowError):
            sold_date = None

    return {
        "address": safe_str(candidate_row.get("address"), "Unknown address"),
        "sold_price": float(candidate_row.get("price", 0.0)),
        "sold_date": sold_date.isoformat() if sold_date else "",
        "distance_km": float(distance_km) if distance_km is not None and np.isfinite(distance_km) else None,
        "similarity_score": combined_similarity,
        "leaf_similarity_score": leaf_similarity["leaf_similarity_score"],
        "price_per_sqft_similarity": ppsf_similarity,
        "leaf_matches": leaf_similarity["leaf_matches"],
        "leaf_count": leaf_similarity["leaf_count"],
        "subject_price_per_sqft": subject_ppsf,
        "candidate_price_per_sqft": candidate_ppsf,
        "predicted_value": subject_price,
        "yearBuilt": int(candidate_year_built) if candidate_year_built is not None else None,
        "candidate_details": candidate_row,
    }


def rank_comps_with_details(subject: dict[str, Any], top_n: int = 20) -> list[dict[str, Any]]:
    pool = candidate_pool(subject)
    if pool.empty:
        return []

    subject_prediction = predict_house_price(subject)
    subject_price = subject_prediction["predicted_price"]
    subject_living_area = parse_float(subject.get("livingArea"))
    subject_ppsf = price_per_sqft_value(subject_price, subject_living_area)

    results = [
        score_candidate(subject, row.to_dict(), subject_price, subject_ppsf)
        for _, row in pool.iterrows()
    ]
    results.sort(
        key=lambda item: (
            item["similarity_score"],
            -float(item["distance_km"]) if item["distance_km"] is not None else float("-inf"),
        ),
        reverse=True,
    )
    return results[:top_n]


def rank_comps(subject: dict[str, Any], top_n: int = 20) -> list[dict[str, Any]]:
    return [summarize_comp(comp) for comp in rank_comps_with_details(subject, top_n=top_n)]


def confidence_from_comps(comps: list[dict[str, Any]]) -> str:
    if not comps:
        return "low"

    top_score = comps[0]["similarity_score"]
    strong_count = sum(1 for comp in comps[:10] if comp["similarity_score"] >= 0.65)

    if top_score >= 0.82 and strong_count >= 5:
        return "high"
    if top_score >= 0.62 and strong_count >= 2:
        return "medium"
    return "low"


def get_matches_by_period(address: str, start_date: str, end_date: str) -> dict[str, Any]:
    df = load_dataset().copy()
    address_norm = address.strip().lower()
    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()

    if "closeDate_days" in df.columns:
        sale_dates = pd.Timestamp(DATE_ORIGIN) + pd.to_timedelta(df["closeDate_days"], unit="D")
        mask = sale_dates.dt.date.between(start, end, inclusive="both")
        df = df[mask].copy()

    if address_norm:
        df = df[df["address"].astype(str).str.lower().str.contains(address_norm, na=False)].copy()

    results = []
    for _, row in df.head(20).iterrows():
        sale_date = None
        if "closeDate_days" in row and pd.notna(row["closeDate_days"]):
            try:
                sale_date = (DATE_ORIGIN + timedelta(days=int(float(row["closeDate_days"])))).isoformat()
            except (TypeError, ValueError, OverflowError):
                sale_date = ""

        results.append(
            {
                "address": safe_str(row.get("address"), "Unknown address"),
                "sold_price": float(row.get("price", 0.0)),
                "sold_date": sale_date or "",
            }
        )

    return {
        "address": address,
        "start_date": start_date,
        "end_date": end_date,
        "matches": results,
    }
