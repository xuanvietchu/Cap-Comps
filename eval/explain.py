from pathlib import Path
import argparse

import joblib
import shap
import pandas as pd
import numpy as np

from train.train_house_price_pipeline import (
    DataCleaner,
    LogFeatureEngineer,
    MultiQuantileRegressor,
    default_lgbm_params,
)


TARGET_COL = "price"


def load_xy(csv_path):
    df = pd.read_csv(csv_path)

    if TARGET_COL in df.columns:
        y = df[TARGET_COL].copy()
        X = df.drop(columns=[TARGET_COL])
    else:
        y = None
        X = df.copy()

    return X, y


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-path",
        default="./models/house_price_lgbm_pipeline.joblib",
    )
    parser.add_argument(
        "--data-path",
        default="./data/test/test.csv",
    )
    parser.add_argument(
        "--house-idx",
        type=int,
        default=10,
    )
    args = parser.parse_args()

    bundle = joblib.load(args.model_path)
    pipeline = bundle["pipeline"]

    X_raw, y = load_xy(args.data_path)

    feature_pipeline = pipeline[:-1]
    quantile_model = pipeline.named_steps["model"]

    X = feature_pipeline.transform(X_raw)

    model = quantile_model.models_[0.50]

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    shap.summary_plot(shap_values, X)

    house_idx = args.house_idx

    if house_idx >= len(X):
        raise ValueError(
            f"house_idx={house_idx} is out of range. "
            f"Dataset only has {len(X)} rows."
        )

    row = X.iloc[[house_idx]]

    q10_model = quantile_model.models_[0.10]
    q50_model = quantile_model.models_[0.50]
    q90_model = quantile_model.models_[0.90]

    pred_q10 = np.expm1(q10_model.predict(row)[0])
    pred_q50 = np.expm1(q50_model.predict(row)[0])
    pred_q90 = np.expm1(q90_model.predict(row)[0])

    base_log = explainer.expected_value
    base_price = np.expm1(base_log)

    actual_price = None
    if y is not None:
        actual_price = y.iloc[house_idx]
        
    print("\nHouse explanation")
    print("-----------------")
    print(f"House index: {house_idx}")

    print(f"\nPrediction Interval")
    print(f"  Low  (10th percentile): ${pred_q10:,.0f}")
    print(f"  Mid  (50th percentile): ${pred_q50:,.0f}")
    print(f"  High (90th percentile): ${pred_q90:,.0f}")

    print(
        f"\nEstimated Value: "
        f"${pred_q50:,.0f} "
        f"(80% interval: ${pred_q10:,.0f} - ${pred_q90:,.0f})"
    )

    if actual_price is not None:
        print(f"\nActual Price: ${actual_price:,.0f}")

        if pred_q10 <= actual_price <= pred_q90:
            print("Actual price is INSIDE prediction interval")
        else:
            print("Actual price is OUTSIDE prediction interval")

        error_pct = (
            abs(actual_price - pred_q50)
            / actual_price
            * 100
        )

        print(f"Median Prediction Error: {error_pct:.2f}%")

    row_shap = shap_values[house_idx]

    effect_df = pd.DataFrame({
        "feature": X.columns,
        "value": X.iloc[house_idx].values,
        "shap_log_effect": row_shap,
        "approx_pct_effect": (np.exp(row_shap) - 1) * 100,
    })

    effect_df["abs_effect"] = effect_df["shap_log_effect"].abs()

    effect_df = (
        effect_df
        .sort_values("abs_effect", ascending=False)
        .drop(columns=["abs_effect"])
    )

    print("\nTop SHAP effects")
    print("----------------")
    print(effect_df.head(20).to_string(index=False))

    explanation = shap.Explanation(
        values=shap_values[house_idx],
        base_values=explainer.expected_value,
        data=X.iloc[house_idx],
        feature_names=X.columns,
    )

    shap.plots.waterfall(explanation)


if __name__ == "__main__":
    main()