from __future__ import annotations

from typing import Any

from api.gemini_client import call_gemini, parse_json_object, parts_from_response, text_from_parts


FORM_FIELDS = {
    "address",
    "assessmentClass",
    "zoning",
    "bathroomsCount",
    "bedroomsCount",
    "livingArea",
    "lotSizeArea",
    "yearBuilt",
    "garage",
    "houseStyle",
    "basement",
    "neighbourhoodName",
    "L_basement2_status",
    "L_basement1_size",
    "L_basement1_status",
    "exterior",
    "floor",
    "foundation",
    "heat",
    "roof",
    "extra",
}

ARRAY_FIELDS = {"exterior", "floor", "foundation", "heat", "roof", "extra"}


def _clean_details(raw: dict[str, Any]) -> dict[str, Any]:
    """Keep only frontend-supported fields and normalize array-like values."""
    details: dict[str, Any] = {}
    for key, value in raw.items():
        if key not in FORM_FIELDS or value in (None, ""):
            continue
        if key in ARRAY_FIELDS:
            if isinstance(value, list):
                details[key] = [str(item).strip() for item in value if str(item).strip()]
            elif isinstance(value, str) and value.strip():
                details[key] = [item.strip() for item in value.split(",") if item.strip()]
            continue
        details[key] = str(value).strip()
    return details


def parse_house_details_pdf(
    data_base64: str,
    mime_type: str = "application/pdf",
) -> dict[str, Any]:
    """Use Gemini to extract structured house details from a PDF payload."""
    field_list = ", ".join(sorted(FORM_FIELDS))
    contents = [
        {
            "role": "user",
            "parts": [
                {
                    "text": (
                        "Extract residential property values from the entire PDF, using all pages as context."
                        "Return only compact JSON with keys details and summary. "
                        "details may contain only these form field names: "
                        f"{field_list}. "
                        "These fields fill the first page of the house-details form only; do not return search constraint fields. "
                        "Infer the correct exact field key from the meaning of the PDF text, even when the PDF uses different wording. "
                        "Always return the exact form key names, not generic PDF labels such as bathrooms, bedrooms, buildingType, or lotSize. "
                        "The target form needs: bathroomsCount as total bathrooms; bedroomsCount as total bedrooms; neighbourhoodName can be extracted from the address "
                        "livingArea is the size of the finished/interior floor area by sqft; lotSizeArea as lot or parcel area in Square Metres; Accept these numbers as float "
                        "houseStyle as the building type or architectural style;"
                        "garage as the parking type or existance of any thing garage related itself; If the parking type has garage or if there is a garage, then the garage is 1."
                        "basement1_size and basement1_status is the first basement; L_basement2_status as the second basement, suite, or lower-level status if a second basement/status is present. "
                        "For houseStyle, prefer one of: 2 storey, bungalow, apartment, bilevel, 4 level split, "
                        "1 and half storey, 3 storey, raised bungalow, 2 and half storey, 5 level split, 3 level split, other. "
                        "If Building Type is detached single family and no more specific style is present, use other. "
                        "Normalize basement to one of: finished, unfinished, partially finished, no basement. "
                        "Normalize L_basement2_status to one of: Fully Finished, Partly Finished, Unfinished, No Basement. "
                        "basement as basement development; basement is considered finished if all basement in the documents are finished; If any basement is unfinished, this field is unfinished. "
                        "Use strings for scalar values and arrays of strings for exterior, floor, foundation, heat, roof, and extra. "
                        "Use assessmentClass as residential or condo when clear. Property Type and assessmentClass are the same thing. Omit fields that are not present or uncertain."
                    )
                },
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": data_base64,
                    }
                },
            ],
        }
    ]
    response = call_gemini(
        contents,
        system_text="You parse real estate PDFs into form fields. Return JSON only.",
        use_tools=False,
    )
    parsed = parse_json_object(text_from_parts(parts_from_response(response)))
    raw_details = parsed.get("details")
    return {
        "details": _clean_details(raw_details if isinstance(raw_details, dict) else {}),
        "summary": str(parsed.get("summary") or ""),
    }
