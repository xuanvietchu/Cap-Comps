import argparse
import joblib
import numpy as np
import pandas as pd

from train.train_house_price_pipeline import (
    DataCleaner,
    LogFeatureEngineer,
    MultiQuantileRegressor,
    default_lgbm_params,
)

TARGET_COL = "price"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", default="./models/house_price_lgbm_pipeline.joblib")
    parser.add_argument("--data-path", default="./data/test/test.csv")
    args = parser.parse_args()

    bundle = joblib.load(args.model_path)
    pipeline = bundle["pipeline"]

    df = pd.read_csv(args.data_path)

    y_true = df[TARGET_COL].astype(float)
    X_raw = df.drop(columns=[TARGET_COL])

    feature_pipeline = pipeline[:-1]
    quantile_model = pipeline.named_steps["model"]

    X = feature_pipeline.transform(X_raw)

    q10_model = quantile_model.models_[0.10]
    q50_model = quantile_model.models_[0.50]
    q90_model = quantile_model.models_[0.90]

    pred_low = np.expm1(q10_model.predict(X))
    pred_mid = np.expm1(q50_model.predict(X))
    pred_high = np.expm1(q90_model.predict(X))

    # Fix quantile crossing just in case
    ordered = np.sort(
        np.vstack([pred_low, pred_mid, pred_high]).T,
        axis=1,
    )

    pred_low = ordered[:, 0]
    pred_mid = ordered[:, 1]
    pred_high = ordered[:, 2]

    inside = (y_true >= pred_low) & (y_true <= pred_high)

    coverage = inside.mean() * 100
    interval_width = pred_high - pred_low
    median_width = np.median(interval_width)
    mean_width = np.mean(interval_width)

    result_df = pd.DataFrame({
        "actual_price": y_true,
        "pred_low_q10": pred_low,
        "pred_mid_q50": pred_mid,
        "pred_high_q90": pred_high,
        "inside_interval": inside,
        "interval_width": interval_width,
        "abs_error_mid": np.abs(y_true - pred_mid),
        "ape_mid_percent": np.abs(y_true - pred_mid) / y_true * 100,
    })

    print("\nInterval Coverage Test")
    print("----------------------")
    print(f"Rows tested: {len(result_df)}")
    print(f"Inside interval: {inside.sum()}")
    print(f"Outside interval: {(~inside).sum()}")
    print(f"Coverage: {coverage:.2f}%")
    print(f"Median interval width: ${median_width:,.0f}")
    print(f"Mean interval width: ${mean_width:,.0f}")

    print("\nInside interval?")
    print(result_df["inside_interval"].value_counts())

    # result_df.to_csv("./data/test/test_interval_results.csv", index=False)
    # print("\nSaved results to:")
    # print("./data/test/test_interval_results.csv")


if __name__ == "__main__":
    # python -m eval.test_interval_coverage
    main()