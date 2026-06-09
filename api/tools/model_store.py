from __future__ import annotations

import json
import sys
from datetime import date
from functools import lru_cache
from typing import Any

import joblib
import numpy as np
import pandas as pd
import shap

from api.tools.tool_utils import (
    DATE_ORIGIN,
    METRICS_PATH,
    MODEL_PATH,
    NON_MODEL_COLUMNS,
    TRAIN_DATASET_PATH,
    format_currency,
    format_number,
)
from train.train_house_price_pipeline import DataCleaner, LogFeatureEngineer, MultiQuantileRegressor


@lru_cache(maxsize=1)
def ensure_legacy_pickle_classes() -> None:
    main_mod = sys.modules.get("__main__")
    if main_mod is None:
        return

    legacy_classes = {
        "DataCleaner": DataCleaner,
        "LogFeatureEngineer": LogFeatureEngineer,
        "MultiQuantileRegressor": MultiQuantileRegressor,
    }
    for name, cls in legacy_classes.items():
        if not hasattr(main_mod, name):
            setattr(main_mod, name, cls)


@lru_cache(maxsize=1)
def load_bundle() -> dict[str, Any]:
    ensure_legacy_pickle_classes()
    return joblib.load(MODEL_PATH)


@lru_cache(maxsize=1)
def load_dataset() -> pd.DataFrame:
    return pd.read_csv(TRAIN_DATASET_PATH)


@lru_cache(maxsize=1)
def load_metrics() -> dict[str, Any]:
    if METRICS_PATH.exists():
        return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    return {}


def model_columns() -> list[str]:
    df = load_dataset()
    return [col for col in df.columns if col not in NON_MODEL_COLUMNS]


def current_close_date_days() -> int:
    return (date.today() - DATE_ORIGIN).days


def build_model_frame(details: dict[str, Any]) -> pd.DataFrame:
    data = {}
    for col in model_columns():
        if col == "closeDate_days":
            value = details.get(col)
            data[col] = current_close_date_days() if value in {None, ""} else value
        else:
            data[col] = details.get(col, np.nan)

    frame = pd.DataFrame([data])
    return frame[model_columns()]


def transform_for_model(details: dict[str, Any]) -> pd.DataFrame:
    bundle = load_bundle()
    pipeline = bundle["pipeline"]
    return pipeline[:-1].transform(build_model_frame(details))


def quantile_model():
    bundle = load_bundle()
    pipeline = bundle["pipeline"]
    model = pipeline.named_steps["model"]
    if hasattr(model, "models_") and 0.50 in model.models_:
        return model.models_[0.50]
    return model


@lru_cache(maxsize=1)
def price_shap_explainer():
    return shap.TreeExplainer(quantile_model())


def model_overview_text() -> str:
    metrics = load_metrics()
    valid = metrics.get("valid", {})
    test = metrics.get("test", {})

    lines = [
        "Model overview:",
        "This project uses a LightGBM quantile pipeline that predicts a low / median / high price band.",
        "The median prediction is the main estimate, and the interval width is used as uncertainty.",
    ]

    if valid:
        lines.append(
            f"Validation performance: MAE {format_currency(valid.get('MAE'))}, "
            f"RMSLE {format_number(valid.get('RMSLE'), 3)}, "
            f"median absolute error {format_currency(valid.get('MedianAE'))}."
        )
    if test:
        lines.append(
            f"Test performance: MAE {format_currency(test.get('MAE'))}, "
            f"RMSLE {format_number(test.get('RMSLE'), 3)}, "
            f"median absolute error {format_currency(test.get('MedianAE'))}."
        )

    lines.append(
        "The model leans on location, size, age, house style, basement finish, exterior and finish flags, and market timing."
    )
    lines.append(
        "Comp ranking uses a combined similarity score, while distance, square footage, and year tolerances are applied separately."
    )
    return " ".join(lines)
