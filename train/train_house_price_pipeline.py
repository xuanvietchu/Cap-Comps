"""
Train a LightGBM house-price model with reusable feature-engineering pipelines.

This script refactors the notebook workflow into a .py file:
- load cleaned CSV
- filter bad assessment classes
- time-based train/validation/test split
- transform raw columns with sklearn-style Pipeline transformers
- train 3 LightGBM quantile models: low / median / high
- evaluate on validation and test sets
- save the fitted pipeline bundle with joblib

Example:
    python train_house_price_pipeline.py \
        --data-path ../data/train/data_clean.csv \
        --model-path models/house_price_lgbm_pipeline.joblib
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, Optional

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.base import BaseEstimator, RegressorMixin, TransformerMixin, clone
from sklearn.pipeline import Pipeline


CAT_COLS = [
    "assessmentClass",
    "zoning",
    "houseStyle",
    "basement",
    "neighbourhoodName",
    "L_basement2_status",
    "L_basement1_size",
    "L_basement1_status",
]

DROP_COLS = ["propertyUrl"]
TARGET_COL = "price"
DATE_COL = "closeDate_days"


class DataCleaner(BaseEstimator, TransformerMixin):
    def __init__(
        self,
        cat_cols=None,
        drop_cols=None,
        filter_other_assessment=True,
    ):
        self.cat_cols = cat_cols
        self.drop_cols = drop_cols
        self.filter_other_assessment = filter_other_assessment

    def fit(self, X: pd.DataFrame, y=None):
        cat_cols = CAT_COLS if self.cat_cols is None else self.cat_cols
        drop_cols = DROP_COLS if self.drop_cols is None else self.drop_cols

        self.cat_cols_ = [col for col in cat_cols if col in X.columns]
        self.drop_cols_ = list(drop_cols)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()

        if self.filter_other_assessment and "assessmentClass" in X.columns:
            X = X[X["assessmentClass"] != "other"].copy()

        X = X.drop(columns=self.drop_cols_, errors="ignore")

        for col in X.columns:
            if col in self.cat_cols_:
                X[col] = X[col].astype("category")
            else:
                X[col] = pd.to_numeric(X[col], errors="coerce")

        return X


class LogFeatureEngineer(BaseEstimator, TransformerMixin):
    def __init__(self, log_features=None, drop_original=True):
        self.log_features = log_features
        self.drop_original = drop_original

    def fit(self, X: pd.DataFrame, y=None):
        self.log_features_ = self.log_features or {
            "livingArea": "log_livingArea",
            "lotSizeArea": "log_lotSizeArea",
        }
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()

        for source_col, new_col in self.log_features_.items():
            if source_col in X.columns:
                values = pd.to_numeric(X[source_col], errors="coerce")
                X[new_col] = np.log1p(values.clip(lower=0))

        if self.drop_original:
            X = X.drop(columns=list(self.log_features_.keys()), errors="ignore")

        return X


class MultiQuantileRegressor(BaseEstimator, RegressorMixin):
    """Fit low / median / high quantile LightGBM regressors in one estimator."""

    def __init__(self, base_params: Optional[dict] = None, quantiles=(0.10, 0.50, 0.90)):
        self.base_params = base_params
        self.quantiles = quantiles

    def fit(self, X: pd.DataFrame, y: pd.Series):
        params = self.base_params or default_lgbm_params()
        self.models_ = {}

        for q in self.quantiles:
            model = LGBMRegressor(**params, objective="quantile", alpha=q)
            model.fit(X, y)
            self.models_[q] = model

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Return the median prediction in log-price space."""
        median_q = 0.50 if 0.50 in self.models_ else sorted(self.models_)[len(self.models_) // 2]
        return self.models_[median_q].predict(X)

    def predict_interval(self, X: pd.DataFrame) -> pd.DataFrame:
        """Return low / median / high predictions in original price space."""
        preds = {}
        for q, model in self.models_.items():
            preds[f"q{int(q * 100):02d}"] = np.expm1(model.predict(X))

        out = pd.DataFrame(preds, index=X.index)

        # Make intervals safe in case quantile crossing happens.
        if {"q10", "q50", "q90"}.issubset(out.columns):
            ordered = np.sort(out[["q10", "q50", "q90"]].to_numpy(), axis=1)
            out[["predictedValueLow", "predictedValue", "predictedValueHigh"]] = ordered

        return out


def default_lgbm_params() -> dict:
    return {
        "n_estimators": 300,
        "learning_rate": 0.05,
        "num_leaves": 31,
        "min_child_samples": 25,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_lambda": 3.0,
        "random_state": 42,
        "n_jobs": -1,
        "verbose": -1,
    }


def regression_metrics(y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, float]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.maximum(np.asarray(y_pred, dtype=float), 1)

    return {
        "MAE": float(np.mean(np.abs(y_true - y_pred))),
        "RMSE": float(np.sqrt(np.mean((y_true - y_pred) ** 2))),
        "RMSLE": float(np.sqrt(np.mean((np.log1p(y_true) - np.log1p(y_pred)) ** 2))),
        "MAPE%": float(np.mean(np.abs((y_true - y_pred) / np.maximum(y_true, 1))) * 100),
        "MedianAE": float(np.median(np.abs(y_true - y_pred))),
    }


def split_by_time(df: pd.DataFrame, train_size=0.7, valid_size_of_remaining=0.5):
    if DATE_COL not in df.columns:
        raise ValueError(f"Missing required time split column: {DATE_COL}")

    df = df.sort_values(DATE_COL).reset_index(drop=True)

    train_end = int(len(df) * train_size)
    train_df = df.iloc[:train_end].copy()
    holdout_df = df.iloc[train_end:].copy()

    valid_end = int(len(holdout_df) * valid_size_of_remaining)
    valid_df = holdout_df.iloc[:valid_end].copy()
    test_df = holdout_df.iloc[valid_end:].copy()

    return train_df, valid_df, test_df


def prepare_xy(df: pd.DataFrame):
    df = df.copy()
    df = df[(df[TARGET_COL].notna()) & (df[TARGET_COL] > 0)].copy()

    y = np.log1p(df[TARGET_COL])
    X = df.drop(columns=[TARGET_COL], errors="ignore")

    return X, y


def make_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            ("clean", DataCleaner()),
            ("features", LogFeatureEngineer()),
            ("model", MultiQuantileRegressor(base_params=default_lgbm_params())),
        ]
    )


def train(data_path: str | Path, model_path: str | Path):
    raw_df = pd.read_csv(data_path)

    # Apply cleaning once before splitting so rows filtered by assessmentClass do not break alignment.
    cleaner = DataCleaner()
    cleaned_df = cleaner.fit_transform(raw_df)

    train_df, valid_df, test_df = split_by_time(cleaned_df)

    # Create directories
    Path("./data/train").mkdir(parents=True, exist_ok=True)
    Path("./data/valid").mkdir(parents=True, exist_ok=True)
    Path("./data/test").mkdir(parents=True, exist_ok=True)

    # Save splits
    train_df.to_csv("./data/train/train.csv", index=False)
    valid_df.to_csv("./data/valid/valid.csv", index=False)
    test_df.to_csv("./data/test/test.csv", index=False)

    X_train, y_train = prepare_xy(train_df)
    X_valid, y_valid = prepare_xy(valid_df)
    X_test, y_test = prepare_xy(test_df)

    pipeline = Pipeline(
        steps=[
            # Data was already cleaned before splitting; keep this for future inference consistency.
            ("clean", clone(cleaner)),
            ("features", LogFeatureEngineer()),
            ("model", MultiQuantileRegressor(base_params=default_lgbm_params())),
        ]
    )

    pipeline.fit(X_train, y_train)

    valid_pred = np.expm1(pipeline.predict(X_valid))
    test_pred = np.expm1(pipeline.predict(X_test))

    train_pred = np.expm1(pipeline.predict(X_train))

    metrics = {
        "train_rows": int(len(X_train)),
        "valid_rows": int(len(X_valid)),
        "test_rows": int(len(X_test)),
        "train": regression_metrics(np.expm1(y_train), train_pred),
        "valid": regression_metrics(np.expm1(y_valid), valid_pred),
        "test": regression_metrics(np.expm1(y_test), test_pred),
    }

    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)

    bundle = {
        "pipeline": pipeline,
        "metrics": metrics,
        "target_transform": "log1p(price)",
        "prediction_inverse_transform": "expm1(prediction)",
        "cat_cols": CAT_COLS,
        "date_col": DATE_COL,
    }

    joblib.dump(bundle, model_path)

    metrics_path = model_path.with_suffix(".metrics.json")
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    return bundle, metrics_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-path", default="./data/train/data_clean.csv")
    parser.add_argument("--model-path", default="./models/house_price_lgbm_pipeline.joblib")
    args = parser.parse_args()

    _, metrics_path = train(args.data_path, args.model_path)
    print(f"Saved model to: {args.model_path}")
    print(f"Saved metrics to: {metrics_path}")
    print(metrics_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
