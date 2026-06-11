from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from api.tools.comp_ranking import rank_comps_with_details, summarize_comp
from api.tools.model_store import price_shap_explainer, quantile_model, transform_for_model
from api.tools.price_tools import predict_house_price
from api.tools.tool_utils import format_feature_value


def shap_array(frame: pd.DataFrame) -> np.ndarray:
    explainer = price_shap_explainer()
    shap_values = explainer.shap_values(frame)
    if isinstance(shap_values, list):
        shap_values = shap_values[0]
    shap_values_array = np.asarray(shap_values, dtype=float)
    if shap_values_array.ndim == 2 and shap_values_array.shape[0] == 1:
        shap_values_array = shap_values_array[0]
    return shap_values_array


def common_shap_drivers(
    subject_frame: pd.DataFrame,
    candidate_frame: pd.DataFrame,
    top_n: int = 3,
) -> list[dict[str, Any]]:
    subject_shap = shap_array(subject_frame)
    candidate_shap = shap_array(candidate_frame)
    shared: list[dict[str, Any]] = []

    for index, feature_name in enumerate(subject_frame.columns):
        subject_effect = float(subject_shap[index])
        candidate_effect = float(candidate_shap[index])
        if not np.isfinite(subject_effect) or not np.isfinite(candidate_effect):
            continue
        if subject_effect * candidate_effect <= 0:
            continue
        shared.append(
            {
                "feature": feature_name,
                "subject_effect": subject_effect,
                "candidate_effect": candidate_effect,
                "direction": "up" if subject_effect > 0 else "down",
                "shared_importance": min(abs(subject_effect), abs(candidate_effect)),
            }
        )

    shared.sort(key=lambda item: item["shared_importance"], reverse=True)
    return [
        {
            "feature": item["feature"],
            "subject_effect": item["subject_effect"],
            "candidate_effect": item["candidate_effect"],
            "direction": item["direction"],
        }
        for item in shared[:top_n]
    ]


def tree_decision_path(tree: dict[str, Any], row: pd.Series, feature_names: list[str]) -> tuple[list[dict[str, Any]], int]:
    node = tree["tree_structure"]
    path: list[dict[str, Any]] = []

    while "leaf_index" not in node:
        feature_index = int(node["split_feature"])
        feature = feature_names[feature_index]
        threshold = node["threshold"]
        decision_type = node.get("decision_type", "<=")
        value = row.iloc[feature_index]

        if pd.isna(value):
            go_left = bool(node.get("default_left", True))
            decision = "missing"
        elif decision_type == "<=":
            go_left = bool(value <= threshold)
            decision = f"{float(value):.4f} <= {float(threshold):.4f}"
        else:
            go_left = bool(value == threshold)
            decision = f"{value} == {threshold}"

        path.append(
            {
                "feature": feature,
                "value": format_feature_value(value),
                "threshold": threshold,
                "decision_type": decision_type,
                "decision": decision,
                "go": "left" if go_left else "right",
            }
        )
        node = node["left_child"] if go_left else node["right_child"]

    return path, int(node["leaf_index"])


def format_decision_path(path: list[dict[str, Any]]) -> list[str]:
    return [
        f"  {step['feature']}: {step['decision']} -> {step['go']}"
        for step in path
    ]


def decision_path_comparison(
    subject_frame: pd.DataFrame,
    candidate_frame: pd.DataFrame,
    max_trees: int = 5,
) -> dict[str, Any]:
    model = quantile_model()
    subject_leaves = np.asarray(model.predict(subject_frame, pred_leaf=True)).reshape(-1)
    candidate_leaves = np.asarray(model.predict(candidate_frame, pred_leaf=True)).reshape(-1)
    same_tree_mask = subject_leaves == candidate_leaves
    same_tree_indices = np.where(same_tree_mask)[0]
    diff_tree_indices = np.where(~same_tree_mask)[0]
    total_trees = int(min(subject_leaves.size, candidate_leaves.size))
    shared_count = int(np.sum(same_tree_mask))
    similarity = float(shared_count / total_trees) if total_trees else 0.0

    tree_indices = list(same_tree_indices[:max_trees])
    showing_shared = True
    if not tree_indices:
        tree_indices = list(diff_tree_indices[:max_trees])
        showing_shared = False

    booster_dump = model.booster_.dump_model()
    trees = booster_dump["tree_info"]
    feature_names = list(subject_frame.columns)
    tree_comparisons: list[dict[str, Any]] = []
    output_lines = [
        "Leaf Similarity",
        "---------------",
        "House A: subject",
        "House B: comp",
        f"Shared leaves: {shared_count} / {total_trees} ({similarity * 100:.2f}%)",
    ]
    if not showing_shared:
        output_lines.extend(["", "No shared-leaf trees found. Showing first different trees instead."])

    for tree_index in tree_indices:
        tree = trees[int(tree_index)]
        subject_path, subject_leaf = tree_decision_path(tree, subject_frame.iloc[0], feature_names)
        candidate_path, candidate_leaf = tree_decision_path(tree, candidate_frame.iloc[0], feature_names)
        same_leaf = subject_leaf == candidate_leaf

        tree_comparisons.append(
            {
                "tree_index": int(tree_index),
                "subject_leaf": subject_leaf,
                "candidate_leaf": candidate_leaf,
                "same_leaf": same_leaf,
                "subject_path": subject_path,
                "candidate_path": candidate_path,
            }
        )
        output_lines.extend(
            [
                "",
                "=" * 80,
                f"Tree {int(tree_index)}",
                f"House A leaf: {subject_leaf}",
                f"House B leaf: {candidate_leaf}",
                f"Same leaf: {same_leaf}",
                "",
                "House A decision path:",
                *format_decision_path(subject_path),
                "",
                "House B decision path:",
                *format_decision_path(candidate_path),
            ]
        )

    return {
        "shared_leaf_count": shared_count,
        "total_trees": total_trees,
        "leaf_similarity": similarity,
        "tree_comparisons": tree_comparisons,
        "path_comparison_output": "\n".join(output_lines),
    }


def explain_comp_similarity(subject: dict[str, Any], comp: dict[str, Any]) -> dict[str, Any]:
    candidate_details = comp.get("candidate_details")
    if candidate_details is None:
        return {
            "address": comp["address"],
            "summary": "Not enough candidate details to explain why this comp is similar.",
        }

    subject_frame = transform_for_model(subject)
    candidate_frame = transform_for_model(candidate_details)
    subject_model_price = predict_house_price(subject)["predicted_price"]
    candidate_model_price = predict_house_price(candidate_details)["predicted_price"]
    shared_drivers = common_shap_drivers(subject_frame, candidate_frame, top_n=3)
    path_comparison = decision_path_comparison(subject_frame, candidate_frame, max_trees=5)
    leaf_matches = comp["leaf_matches"]
    leaf_count = comp["leaf_count"]
    leaf_match_pct = float(leaf_matches / leaf_count) if leaf_count else 0.0
    shared_driver_notes = [
        f"{item['feature']} pushes both properties {item['direction']} in the model."
        for item in shared_drivers
    ]

    return {
        "address": comp["address"],
        "sold_price": comp["sold_price"],
        "similarity_score": comp["similarity_score"],
        "leaf_similarity_score": comp["leaf_similarity_score"],
        "leaf_matches": leaf_matches,
        "leaf_count": leaf_count,
        "leaf_match_percent": leaf_match_pct,
        "subject_modeled_price": subject_model_price,
        "candidate_modeled_price": candidate_model_price,
        "candidate_actual_price": comp["sold_price"],
        "shared_drivers": shared_drivers,
        "shared_driver_notes": shared_driver_notes,
        "decision_path_comparison": path_comparison,
        "path_comparison_output": path_comparison["path_comparison_output"],
        "explanation": (
            f"The model places both homes in the same leaf in {leaf_matches} out of {leaf_count} trees, "
            f"which means they follow similar decision rules for those trees. "
            f"The model predicts ${candidate_model_price:,.0f} for the comp and ${subject_model_price:,.0f} for the subject."
        ),
    }


def explain_comps(
    subject: dict[str, Any],
    top_n: int = 5,
    comps_with_details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if comps_with_details is None:
        comps_with_details = rank_comps_with_details(subject, top_n=top_n)
    else:
        comps_with_details = comps_with_details[:top_n]

    top_comps = [summarize_comp(comp) for comp in comps_with_details]
    explanations = [explain_comp_similarity(subject, comp) for comp in comps_with_details]

    return {
        "kind": "comps",
        "top_comp": top_comps[0] if top_comps else None,
        "top_comp_count": min(len(top_comps), top_n),
        "top_comps": top_comps,
        "comp_explanations": explanations,
    }
