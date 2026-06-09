# python -m eval.explain
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

def get_leaf_indices(model, X):
    return model.predict(X, pred_leaf=True)


def trace_tree_path(tree, row, feature_names):
    node = tree["tree_structure"]
    path = []

    while "leaf_index" not in node:
        feat_idx = node["split_feature"]
        feat = feature_names[feat_idx]
        threshold = node["threshold"]
        decision_type = node.get("decision_type", "<=")
        value = row.iloc[feat_idx]

        if pd.isna(value):
            go_left = node.get("default_left", True)
            decision = "missing"
        elif decision_type == "<=":
            go_left = value <= threshold
            decision = f"{value:.4f} <= {threshold:.4f}"
        else:
            go_left = value == threshold
            decision = f"{value} == {threshold}"

        path.append({
            "feature": feat,
            "value": value,
            "threshold": threshold,
            "decision_type": decision_type,
            "decision": decision,
            "go": "left" if go_left else "right",
        })

        node = node["left_child"] if go_left else node["right_child"]

    return path, node["leaf_index"]


def compare_leaf_similarity(model, X, idx_a, idx_b):
    leaves = get_leaf_indices(model, X)

    leaves_a = leaves[idx_a]
    leaves_b = leaves[idx_b]

    same_tree_mask = leaves_a == leaves_b
    same_count = same_tree_mask.sum()
    total_trees = len(leaves_a)

    return {
        "same_count": same_count,
        "total_trees": total_trees,
        "similarity": same_count / total_trees,
        "same_tree_indices": np.where(same_tree_mask)[0],
        "diff_tree_indices": np.where(~same_tree_mask)[0],
        "leaves_a": leaves_a,
        "leaves_b": leaves_b,
    }


def print_decision_path_comparison(model, X, idx_a, idx_b, max_trees=5):
    result = compare_leaf_similarity(model, X, idx_a, idx_b)

    print("\nLeaf Similarity")
    print("---------------")
    print(f"House A index: {idx_a}")
    print(f"House B index: {idx_b}")
    print(
        f"Shared leaves: {result['same_count']} / {result['total_trees']} "
        f"({result['similarity'] * 100:.2f}%)"
    )

    booster_dump = model.booster_.dump_model()
    trees = booster_dump["tree_info"]
    feature_names = list(X.columns)

    tree_indices = list(result["same_tree_indices"][:max_trees])

    if len(tree_indices) == 0:
        print("\nNo shared-leaf trees found. Showing first different trees instead.")
        tree_indices = list(result["diff_tree_indices"][:max_trees])

    for tree_idx in tree_indices:
        tree = trees[tree_idx]

        path_a, leaf_a = trace_tree_path(
            tree,
            X.iloc[idx_a],
            feature_names,
        )

        path_b, leaf_b = trace_tree_path(
            tree,
            X.iloc[idx_b],
            feature_names,
        )

        print("\n" + "=" * 80)
        print(f"Tree {tree_idx}")
        print(f"House A leaf: {leaf_a}")
        print(f"House B leaf: {leaf_b}")
        print(f"Same leaf: {leaf_a == leaf_b}")

        print("\nHouse A decision path:")
        for step in path_a:
            print(
                f"  {step['feature']}: {step['decision']} "
                f"-> {step['go']}"
            )

        print("\nHouse B decision path:")
        for step in path_b:
            print(
                f"  {step['feature']}: {step['decision']} "
                f"-> {step['go']}"
            )


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
    parser.add_argument("--compare-idx", type=int, default=11)
    parser.add_argument("--top-path-trees", type=int, default=10)
    args = parser.parse_args()

    bundle = joblib.load(args.model_path)
    pipeline = bundle["pipeline"]

    X_raw, y = load_xy(args.data_path)

    feature_pipeline = pipeline[:-1]
    quantile_model = pipeline.named_steps["model"]

    X = feature_pipeline.transform(X_raw)

    model = quantile_model.models_[0.50]

    explainer = shap.TreeExplainer(model)
    X = X.drop(columns=["address"])
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

    if args.compare_idx is not None:
        if args.compare_idx >= len(X):
            raise ValueError(
                f"compare_idx={args.compare_idx} is out of range. "
                f"Dataset only has {len(X)} rows."
            )

        print_decision_path_comparison(
            model=model,
            X=X,
            idx_a=args.house_idx,
            idx_b=args.compare_idx,
            max_trees=args.top_path_trees,
        )

    shap.plots.waterfall(explanation)


if __name__ == "__main__":
    main()