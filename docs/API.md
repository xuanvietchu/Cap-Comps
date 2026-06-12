# API Reference

The backend is a FastAPI service for property valuation and comparable sale analysis. The chat API streams trace events and then returns the final agent response used by the Next.js UI.

Base URL in local development:

```text
http://localhost:8000
```

Interactive OpenAPI documentation is available once the backend is running:

```text
http://localhost:8000/docs
```

## Authentication

The local API does not require client authentication. The server must have `GOOGLE_API_KEY` configured in `.env` so it can call Gemini for intent analysis, PDF parsing, and final answer synthesis.

## POST /chat/stream

Runs an agent turn and streams newline-delimited JSON events. This is the endpoint used by the frontend so users can see trace updates while the backend is working.

Request body:

```json
{
  "message": "Show me the top 10 comps for this house",
  "house_details": {
    "address": "123 Main St",
    "assessmentClass": "residential",
    "livingArea": 1800,
    "lotSizeArea": 450,
    "yearBuilt": 1998,
    "lat": 53.5461,
    "lon": -113.4938
  },
  "conversation_id": "optional-stable-chat-id",
  "conversation_history": [
    { "role": "user", "content": "What is this house worth?" },
    { "role": "assistant", "content": "The estimated value is..." }
  ]
}
```

Event format:

```json
{
  "type": "trace",
  "event": {
    "phase": "tool",
    "message": "Calling GET_COMPS",
    "data": { "top_n": 10 }
  }
}
```

The final event contains the complete agent response:

```json
{
  "type": "final",
  "response": {
    "answer": "I found comparable sales for the subject property.",
    "conversation_id": "optional-stable-chat-id",
    "confidence_level": "medium",
    "prediction": {
      "predicted_price": 515000,
      "predicted_price_low": 480000,
      "predicted_price_high": 550000,
      "confidence_level": "medium",
      "interval_width": 70000,
      "interval_width_ratio": 0.1359
    },
    "comps": [],
    "intent": "comps",
    "prompt": "gemini:gemini-3.1-flash-lite:tool-driven",
    "explanation": null,
    "display": {
      "show_prediction": false,
      "show_comps": true,
      "show_csv_export": false
    },
    "intent_analysis": {
      "intent": "comps",
      "confidence": "high",
      "summary": "The user asked for comparable sales.",
      "planned_tools": ["GET_COMPS"]
    },
    "agent_trace": [],
    "export_csv": null
  }
}
```

Errors are streamed as:

```json
{ "type": "error", "message": "error details" }
```

Supported intents:

- `price`: predict the subject property price band.
- `comps`: rank comparable sold homes for the subject property.
- `explain`: explain valuation drivers or comparable selection.
- `export`: export the latest comps table as CSV.
- `general`: answer general contextual questions.

## POST /parse-house-pdf

Extracts supported house-detail form fields from a PDF encoded as base64. The endpoint uses Gemini vision/document understanding and returns only fields accepted by the frontend form.

Request body:

```json
{
  "filename": "assessment.pdf",
  "mime_type": "application/pdf",
  "data_base64": "JVBERi0xLjQK..."
}
```

Response body:

```json
{
  "details": {
    "address": "123 Main St",
    "bathroomsCount": "2.5",
    "bedroomsCount": "4",
    "livingArea": "1800",
    "lotSizeArea": "450",
    "yearBuilt": "1998",
    "houseStyle": "2 storey",
    "basement": "finished"
  },
  "summary": "Residential assessment document for 123 Main St."
}
```

Supported form fields include address, class, zoning, bathrooms, bedrooms, living area, lot size, year built, garage, house style, basement, neighbourhood, second basement status, basement size/status, exterior, floor, foundation, heat, roof, and extra features.

## GET /health

Returns a lightweight status check.

```json
{ "status": "ok" }
```

## Important Response Fields

`prediction` is populated when a price estimate or comparable search runs. The backend uses the median quantile prediction as the main value and derives confidence from interval width.

`comps` is populated when comparable ranking runs. Ranking combines LightGBM leaf similarity with price-per-square-foot similarity, after filtering by class, square footage tolerance, year-built tolerance, and distance when coordinates are available.

`explanation` is populated for valuation explanation requests. It contains top positive and negative model drivers.

`export_csv` is populated after a successful CSV export request. It contains the CSV text and metadata for the latest comps table in the conversation.

`agent_trace` contains debug-friendly orchestration events. The frontend can display these events to show which intent and tools were selected.
