from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from api.tools.model_store import build_model_frame, load_bundle, price_shap_explainer
from api.tools.tool_utils import format_feature_value


def predict_interval_from_frame(frame: pd.DataFrame) -> dict[str, float]:
    bundle = load_bundle()
    pipeline = bundle["pipeline"]
    model = pipeline.named_steps["model"]
    transformed = pipeline[:-1].transform(frame)

    if hasattr(model, "predict_interval"):
        interval = model.predict_interval(transformed).iloc[0].to_dict()
        return {
            "low": float(interval["predictedValueLow"]),
            "mid": float(interval["predictedValue"]),
            "high": float(interval["predictedValueHigh"]),
        }

    if hasattr(model, "models_"):
        q10 = np.expm1(model.models_[0.10].predict(transformed))[0]
        q50 = np.expm1(model.models_[0.50].predict(transformed))[0]
        q90 = np.expm1(model.models_[0.90].predict(transformed))[0]
        ordered = sorted([float(q10), float(q50), float(q90)])
        return {"low": ordered[0], "mid": ordered[1], "high": ordered[2]}

    pred = float(np.expm1(pipeline.predict(transformed)[0]))
    return {"low": pred, "mid": pred, "high": pred}


def predict_house_price(details: dict[str, Any]) -> dict[str, Any]:
    frame = build_model_frame(details)
    interval = predict_interval_from_frame(frame)
    midpoint = max(interval["mid"], 1.0)
    width = max(interval["high"] - interval["low"], 0.0)
    width_ratio = width / midpoint

    if width_ratio <= 0.18:
        confidence = "high"
    elif width_ratio <= 0.35:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "predicted_price": interval["mid"],
        "predicted_price_low": interval["low"],
        "predicted_price_high": interval["high"],
        "confidence_level": confidence,
        "interval_width": width,
        "interval_width_ratio": width_ratio,
    }


def explain_house_price(details: dict[str, Any], top_n: int = 5) -> dict[str, Any]:
    frame = build_model_frame(details)
    bundle = load_bundle()
    transformed = bundle["pipeline"][:-1].transform(frame)
    explainer = price_shap_explainer()
    shap_values = explainer.shap_values(transformed)

    if isinstance(shap_values, list):
        shap_values = shap_values[0]

    row = transformed.iloc[0]
    row_values = np.asarray(shap_values[0], dtype=float)

    effects: list[dict[str, Any]] = []
    for feature_name, feature_value, effect in zip(transformed.columns, row.tolist(), row_values):
        if not np.isfinite(effect):
            continue

        effects.append(
            {
                "feature": feature_name,
                "value": format_feature_value(feature_value),
                "shap_log_effect": float(effect),
                "approx_pct_effect": float((np.exp(effect) - 1) * 100),
                "direction": "up" if effect > 0 else "down" if effect < 0 else "neutral",
            }
        )

    positive = sorted(
        (item for item in effects if item["shap_log_effect"] > 0),
        key=lambda item: item["shap_log_effect"],
        reverse=True,
    )[:top_n]
    negative = sorted(
        (item for item in effects if item["shap_log_effect"] < 0),
        key=lambda item: item["shap_log_effect"],
    )[:top_n]

    return {
        "kind": "price",
        "predicted_price": predict_house_price(details)["predicted_price"],
        "top_positive": positive,
        "top_negative": negative,
        "feature_count": len(effects),
    }
