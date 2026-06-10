"""Compatibility exports for housing comps tools.

The implementation is split across focused modules:
- model_store.py: model/data loading and feature transforms
- price_tools.py: price prediction and price explanation
- comp_ranking.py: comparable selection and scoring
- comp_explanations.py: comp explanation and decision-path comparison
"""

from __future__ import annotations

from api.tools.comp_explanations import explain_comps
from api.tools.comp_ranking import (
    candidate_pool as get_candidate_pool,
    confidence_from_comps,
    get_matches_by_period,
    infer_search_constraints,
    leaf_similarity_score,
    price_per_sqft_similarity,
    price_per_sqft_value,
    rank_comps,
    rank_comps_with_details,
    summarize_comp,
)
from api.tools.model_store import (
    build_model_frame,
    current_close_date_days,
    load_metrics,
    model_columns,
    model_overview_text,
    transform_for_model,
)
from api.tools.price_tools import explain_house_price, predict_house_price
from api.tools.tool_utils import parse_float as _parse_float
from api.tools.tool_utils import safe_str as _safe_str

__all__ = [
    "_parse_float",
    "_safe_str",
    "build_model_frame",
    "confidence_from_comps",
    "current_close_date_days",
    "explain_comps",
    "explain_house_price",
    "get_candidate_pool",
    "get_matches_by_period",
    "infer_search_constraints",
    "leaf_similarity_score",
    "load_metrics",
    "model_columns",
    "model_overview_text",
    "predict_house_price",
    "price_per_sqft_similarity",
    "price_per_sqft_value",
    "rank_comps",
    "rank_comps_with_details",
    "summarize_comp",
    "transform_for_model",
]
