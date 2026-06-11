from __future__ import annotations

import base64
import csv
import io
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Any

import pandas as pd

from api.tools.tool_utils import ROOT, safe_str


@dataclass
class ExportSelection:
    rows: list[dict[str, Any]]
    requested_addresses: list[str]
    missing_addresses: list[str]
    filename: str


EXPORT_KEYWORDS = ("export", "download", "csv", "spreadsheet")
EXPORT_DATASET_PATH = ROOT / "data" / "train" / "data.csv"


@lru_cache(maxsize=1)
def load_export_dataset() -> pd.DataFrame:
    return pd.read_csv(EXPORT_DATASET_PATH)


def is_export_request(message: str) -> bool:
    lowered = message.lower()
    wants_export = any(keyword in lowered for keyword in EXPORT_KEYWORDS)
    mentions_comps = any(word in lowered for word in ("comp", "comparable", "comparables"))
    return wants_export and ("csv" in lowered or mentions_comps)


def extract_export_count(message: str) -> int | None:
    patterns = [
        r"\b(?:top|first|best)\s+(\d{1,4})\b",
        r"\b(?:export|download|save)\s+(?:the\s+)?(?:top\s+)?(\d{1,4})\b",
        r"\b(\d{1,4})\s+(?:comps?|comparables?|rows)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return max(1, int(match.group(1)))
    return None


def _normalize_address(address: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", safe_str(address).lower()).strip()


def _comp_addresses(last_analysis: dict[str, Any] | None) -> list[str]:
    analysis = last_analysis or {}
    comps = analysis.get("comps_table")
    if not isinstance(comps, list):
        comps = analysis.get("comps")
    if not isinstance(comps, list):
        return []
    addresses = []
    for comp in comps:
        if isinstance(comp, dict):
            address = safe_str(comp.get("address"))
            if address:
                addresses.append(address)
    return addresses


def _mentioned_comp_addresses(message: str, comp_addresses: list[str]) -> list[str]:
    normalized_message = _normalize_address(message)
    selected: list[str] = []
    for address in comp_addresses:
        normalized_address = _normalize_address(address)
        if not normalized_address:
            continue
        address_tokens = [token for token in normalized_address.split() if token]
        house_number = address_tokens[0] if address_tokens else ""
        street_tokens = address_tokens[1:3]
        direct_match = normalized_address in normalized_message
        partial_match = bool(house_number and house_number in normalized_message) and all(
            token in normalized_message for token in street_tokens
        )
        if direct_match or partial_match:
            selected.append(address)
    return selected


def _best_dataset_rows_for_addresses(addresses: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    df = load_export_dataset()
    if "address" not in df.columns:
        return [], addresses

    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    normalized_series = df["address"].map(_normalize_address)

    for address in addresses:
        normalized_address = _normalize_address(address)
        exact = df[normalized_series == normalized_address]
        if not exact.empty:
            rows.append(exact.iloc[0].to_dict())
            continue

        contains = df[normalized_series.str.contains(re.escape(normalized_address), na=False)]
        if not contains.empty:
            rows.append(contains.iloc[0].to_dict())
            continue

        best_index = None
        best_score = 0.0
        for index, candidate in normalized_series.items():
            score = SequenceMatcher(None, normalized_address, candidate).ratio()
            if score > best_score:
                best_index = index
                best_score = score

        if best_index is not None and best_score >= 0.9:
            rows.append(df.loc[best_index].to_dict())
        else:
            missing.append(address)

    return rows, missing


def select_export_rows(
    message: str,
    last_analysis: dict[str, Any] | None,
    top_n: int | None = None,
    addresses: list[str] | None = None,
) -> ExportSelection:
    latest_addresses = _comp_addresses(last_analysis)
    if not latest_addresses:
        return ExportSelection([], [], [], "comps-export.csv")

    mentioned_addresses = addresses or _mentioned_comp_addresses(message, latest_addresses)
    requested_count = top_n or extract_export_count(message)

    if mentioned_addresses:
        requested_addresses = mentioned_addresses
    elif requested_count is not None:
        requested_addresses = latest_addresses[:requested_count]
    else:
        requested_addresses = latest_addresses

    rows, missing = _best_dataset_rows_for_addresses(requested_addresses)
    return ExportSelection(
        rows=rows,
        requested_addresses=requested_addresses,
        missing_addresses=missing,
        filename=f"comps-export-{len(rows) or 'empty'}.csv",
    )


def build_csv_export_payload(
    message: str,
    last_analysis: dict[str, Any] | None,
    top_n: int | None = None,
    addresses: list[str] | None = None,
) -> dict[str, Any]:
    selection = select_export_rows(message, last_analysis, top_n=top_n, addresses=addresses)
    if not selection.rows:
        return {
            "status": "error",
            "filename": selection.filename,
            "row_count": 0,
            "requested_addresses": selection.requested_addresses,
            "missing_addresses": selection.missing_addresses,
            "data_url": None,
            "source_path": str(EXPORT_DATASET_PATH),
        }

    frame = pd.DataFrame(selection.rows)
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False, quoting=csv.QUOTE_MINIMAL)
    csv_text = buffer.getvalue()
    encoded = base64.b64encode(csv_text.encode("utf-8")).decode("ascii")

    return {
        "status": "ready",
        "filename": selection.filename,
        "row_count": len(selection.rows),
        "requested_addresses": selection.requested_addresses,
        "missing_addresses": selection.missing_addresses,
        "data_url": f"data:text/csv;base64,{encoded}",
        "source_path": str(EXPORT_DATASET_PATH),
    }
