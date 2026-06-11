# Cap-Comps

Capcom is a real estate valuation assistant, focusing only on recent Edmonton Residential Properties. It combines a Next.js chat interface, a FastAPI backend, Gemini-powered intent routing and PDF property-detail parser, a LightGBM quantile valuation and comparable sale ranking model.

The [core demo video flow](https://www.loom.com/share/cbf89b3ac0b348f3b26fd1ae86d4137d) is simple: enter or upload property details, ask for a price estimate, request comps, ask why the valuation or comps make sense, then export the comps table as CSV.

## What It Does

- Parses house details from a PDF into the frontend form.
- Predicts a subject property's low, median, and high price band.
- Retrieves and comparable sold homes by Distance, Age, and living constraints
- Ranks comparable sold homes by comparing model leaf similarity and price-per-square-foot.
- Explains valuation drivers for property price with model feature effects.
- Explains why selected comps match the subject property.
- Streams agent trace events so the UI can show what the agent is doing.
- Exports the latest comps table in a conversation as CSV.

## Project Structure

```text
KV/
├── App Layer
  api/                 FastAPI service, Gemini client, agent orchestration, schemas
  api/tools/           Model loading, valuation, comp ranking, explanations, CSV export
  app/                 Next.js chat frontend

├── Data Science Layer
  data/train/train.csv Training dataset used by the model and comp lookup
  models/              Trained LightGBM pipeline and metrics
  train/               Training pipeline code used by the saved model
  clean/               Data cleaning utilities and intermediate work
  eval/                Evaluation utilities
  scraper/             Data collection utilities
  docs/API.md          API reference
```

## Requirements

- Python >= 3.12.13
- npm version >= 10.2.4
- A Google Gemini API key
- Local model artifact at `models/house_price_lgbm_pipeline.joblib`
- Training data at `data/train/train.csv`

## Environment Setup

Create a root `.env` file:

```env
GOOGLE_API_KEY=your_google_api_key_here
```

The backend loads this file from the project root. Without the key, `api/config.py` raises an error at startup.

## Backend Setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn api.main:app --reload --port 8000
```

Health check:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

OpenAPI docs:

```text
http://localhost:8000/docs
```

## Frontend Setup

In a second terminal:

```powershell
cd app
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

The frontend currently calls the backend at `http://localhost:8000/chat/stream`.

## Demo Script

1. Start the backend and frontend.
2. Open the web app and create a new chat.
3. Enter property details manually or upload a PDF.
4. Ask: `What is this house worth?`
5. Ask: `Show me the top 10 comps.`
6. Ask: `Why were <insert_address> selected as a comp?`
7. Ask: `Export the top 10 comps as CSV.`

## API Documentation

See [docs/API.md](docs/API.md) for endpoint details, request and response examples, streaming event format, and important response fields.

## Development Checks

Backend syntax check:

```powershell
python -m py_compile api/comps_service.py api/agent.py api/main.py api/schemas.py api/tools/comps_tools.py
```

Frontend lint:

```powershell
cd app
npm run lint
```

## A few Notes

The strongest technical pieces are the LightGBM comp similarity and quantile price prediction, SHAP explainer, tool-driven agent contract, and streaming trace UI. Essentially, this is 2 projects in 1: a Data Science project for Comps Matches and Feature Engineering; and AI Agent for intent detection, tool usage, and synthesizing comps and pricing explanation from raw tree model; and a next.js web app with Next.js and FastAPI (if you want to consider this a project too).

The scope of this project blown way out of my imagination, partly because I was having a ton of fun and had applicable skills specific to the case, but mainly due to me synthesizing my own data. I cannot find a high quality free public dataset that present a realistic enough situation. The product can only be as good as the data itself, so I took the problems into my own hands. For a smaller coding challenge, I believe providing a curated dataset would dramatically reduce overhead, as data collection is often a minor cost for organizations that already possess the information but can become a major bottleneck for individuals.

Also, I decided to skip the Commercial Case, simply because the data was lacking in both size and richness of information (sparse, missing cols) for me to understand the case study.

I also decided to intentionally leave out key files within the `\scraper` folder and some other files within the context of the Data Science Project. This decision was made to avoid data leakage of relevant individuals and corporations involved.

# 1. Data Science

## Motivation

A good valuation model implicitly learns which property characteristics drive house prices. If a model can accurately estimate a property's value, that same understanding can be leveraged to identify comparable properties (comps) that share similar valuation drivers.

The goal of this component is to build a machine learning model that predicts residential sale prices and serves as a foundation for comps discovery.

---

## Dataset & Feature Engineering

### Data Collection

- Scraped, cleaned, and consolidated approximately **7,000 Edmonton residential property sales** from **December 2025 to May 2026**.
- Data collection and preparation accounted for roughly **40% of the total project effort**.

### Features

To improve predictive performance:

- Property addresses were transformed into **Walk Scores** through additional scraping and enrichment.
- Rare or low-frequency categories were consolidated into an **"Other"** category to reduce sparsity.
- Temporal information was converted into numerical features.
- Multi-label categorical fields were cleaned and standardized.

The final dataset contains **52 engineered features**, including:

- Assessment class
- Zoning
- Bedrooms and bathrooms
- Living area
- Lot size
- Year built
- Garage information
- House style
- Basement status
- Neighbourhood
- Latitude and longitude
- Walk Score
- Exterior materials
- Flooring materials
- Foundation materials
- Roof materials
- Heating sources
- Property accessories
- Sale date

---

## Model

Three separate **LightGBM quantile regression models** were trained using a **70/15/15 train/validation/test time-wise split**:

| Model           | Target Quantile |
| --------------- | --------------- |
| Lower Bound     | 10th Percentile |
| Median Estimate | 50th Percentile |
| Upper Bound     | 90th Percentile |

Each model consists of approximately **300 trees**.

Together, the models produce a prediction interval that can be used to estimate confidence:

| Confidence Level | Prediction Interval Width  |
| ---------------- | -------------------------- |
| High             | < 10% of median prediction |
| Medium           | 10% – 20%                  |
| Low              | > 20%                      |

---

## Results

The model achieved approximately **30% Mean Absolute Percentage Error (MAPE)** on the test set.

In practical terms:

> A property predicted at $100,000 would be expected to sell within roughly ±$30,000 on average.

While individual predictions may deviate more or less than this amount, the model provides a reasonable valuation baseline for an MVP.

### Key Findings

SHAP explanations revealed that the strongest drivers of property value include:

- Zoning
- Property size
- Neighbourhood
- Year built

An interesting observation was that properties located at lower latitudes and longitudes within Edmonton tended to have higher sale prices.

Additional insights can be found in:

```text
train/experiment.ipynb
```

---

## Why This Matters

### Comparable Property Discovery

Comps systems may require extensive manual feature engineering and weighting rules.

This approach allows the valuation model itself to act as the feature engineering layer, capturing complex relationships between property characteristics automatically.

### Explainability

LightGBM provides strong interpretability compared to many neural network approaches.

Using:

- Tree structure analysis
- SHAP explanations

the Agent can generate human-readable explanations that help analysts understand:

- Why a property received a particular valuation
- Which characteristics most influenced the estimate
- What factors make a comparable property relevant

These explanations are then summarized using Gemini.

### Baseline for Future Work

This model serves as:

- A valuation baseline for future neural network approaches
- A comps-ranking baseline for future neural network approaches
- A benchmark against traditional rule-based matching systems

### Personal Learning

Building this pipeline provided valuable domain knowledge about residential real estate valuation and helped inform the design of the overall product.

# 2. AI Agent

## Goal

The AI Agent is the application layer that turns a user's chat message into a controlled real estate workflow.

Gemini is used for language understanding and final response writing, while the actual price estimate, comps ranking, explanations, PDF parsing, and CSV export are handled by backend Python functions.

The agent supports five actions:

| Action             | What it does                                                      |
| ------------------ | ----------------------------------------------------------------- |
| `PREDICT_PRICE`    | Predicts the subject property's low, median, and high price band. |
| `GET_COMPS`        | Finds and ranks comparable sold homes for the subject property.   |
| `EXPLAIN_PRICE`    | Explains the strongest positive and negative price drivers.       |
| `EXPLAIN_COMPS`    | Explains why the selected comps match the subject property.       |
| `EXPORT_COMPS_CSV` | Exports the latest comps table in the conversation as a CSV file. |

---

## Agent Flow

The main agent logic lives in:

```text
api/comps_service.py
api/tool_orchestration.py
api/config.py
api/gemini_client.py
api/conversation_state.py
```

For each chat message, the backend follows this flow:

1. The frontend sends `message`, `house_details`, `conversation_id`, and recent chat history to the API.
2. `build_response()` loads or creates the conversation state.
3. Gemini first performs a small intent analysis step and returns JSON with:
   - `intent`
   - `confidence`
   - `summary`
   - `planned_tools`
4. The agent builds a prompt with the subject property, recent conversation, prior analysis, and requested comp count.
5. Gemini may call one or more approved tools.
6. `invoke_agent_tool()` maps the tool name to a real Python function.
7. Tool results are passed back to Gemini.
8. Gemini writes the final answer using the tool output as the source of truth.
9. The backend returns the answer, prediction, comps, explanation data, display flags, trace events, and export data when available.

This design keeps the language model in charge of conversation and routing, but keeps pricing and comps grounded in deterministic code.

---

## API Endpoints

The FastAPI app is defined in:

```text
api/main.py
```

It exposes four main endpoints:

| Endpoint                | Purpose                                                                      |
| ----------------------- | ---------------------------------------------------------------------------- |
| `POST /chat/stream`     | Runs the same chat turn, but streams trace events before the final response. |
| `POST /parse-house-pdf` | Uses Gemini to extract house details from a PDF.                             |
| `GET /health`           | Returns `{ "status": "ok" }` for a quick backend check.                      |

The frontend uses `/chat/stream` so the user can see agent progress while tools are running.

The stream format is newline-delimited JSON:

```json
{ "type": "trace", "event": { "step": "tool", "detail": "Calling GET_COMPS" } }
{ "type": "final", "response": { "answer": "...", "comps": [] } }
```

---

## Tool Contract

The tool contract is written in `api/config.py`.

Gemini receives only five tool declarations:

```text
PREDICT_PRICE
GET_COMPS
EXPLAIN_PRICE
EXPLAIN_COMPS
EXPORT_COMPS_CSV
```

The prompt tells Gemini to:

- Use only these tools.
- Wait for tool results before answering.
- Avoid making up tool outputs.
- Avoid calling extra tools that are not needed.
- Use `GET_COMPS` only for the selected subject property.
- Use the latest comps table for CSV export instead of running a new search.

Some tools have dependencies:

| Request type      | Required tool order                  |
| ----------------- | ------------------------------------ |
| Price estimate    | `PREDICT_PRICE`                      |
| Comps             | `GET_COMPS`                          |
| Price explanation | `PREDICT_PRICE` then `EXPLAIN_PRICE` |
| Comps explanation | `GET_COMPS` then `EXPLAIN_COMPS`     |
| CSV export        | `EXPORT_COMPS_CSV`                   |

These dependency rules are enforced in `api/tool_orchestration.py`.

---

## Price Tool

The price tool is implemented in:

```text
api/tools/price_tools.py
api/tools/model_store.py
```

`PREDICT_PRICE` builds a model frame from the subject property details and sends it through the saved LightGBM pipeline.

The model returns:

- `predicted_price_low`
- `predicted_price`
- `predicted_price_high`

The API then computes confidence from the width of the prediction interval:

| Confidence | Interval width                         |
| ---------- | -------------------------------------- |
| High       | 10% or less of the median prediction   |
| Medium     | 10% to 20% of the median prediction    |
| Low        | More than 20% of the median prediction |

`EXPLAIN_PRICE` uses SHAP-style values from the model to return:

- Top positive drivers
- Top negative drivers
- Approximate percentage effect
- Direction of each feature effect

Gemini then turns those raw model drivers into a readable explanation.

---

## Comps Tool

The comps ranking logic is implemented in:

```text
api/tools/comp_ranking.py
```

`GET_COMPS` starts by filtering the training dataset to a reasonable candidate pool.

The filters include:

- Same `assessmentClass`, when available
- Living area tolerance, defaulting to 20%
- Year built tolerance, defaulting to 10 years
- Distance from the subject property, defaulting to 3 km when locations are available
- Sold properties with a valid price

Each candidate is then scored with two signals:

1. LightGBM leaf similarity
2. Price-per-square-foot similarity

The final similarity score is:

```text
0.5 * leaf_similarity_score + 0.5 * price_per_sqft_similarity
```

This is the key bridge between the data science model and the agent. The model is not only predicting price; it is also helping define which houses are structurally similar in the model's learned decision paths.

---

## Comp Explanation Tool

The comp explanation logic is implemented in:

```text
api/tools/comp_explanations.py
```

`EXPLAIN_COMPS` keeps the top comp results, then compares the subject and each comp inside the LightGBM model.

It looks at:

- How many trees place the subject and comp in the same leaf.
- The total number of trees compared.
- Shared SHAP-style drivers.
- Example decision paths from matching trees.
- The model price for the subject and the comp.

The raw decision path output is technical, so the prompt tells Gemini to summarize it instead of pasting the raw tree paths into the chat response.

This lets the app answer questions like:

```text
Why were these comps selected?
How are these homes similar?
Why does this comp match the subject?
```

---

## PDF Parser

The PDF parser is implemented in:

```text
api/pdf_form_parser.py
```

The frontend sends a base64 PDF to `POST /parse-house-pdf`.

Gemini reads the PDF and returns only fields that match the house details form, such as:

- Address
- Assessment class
- Zoning
- etc

The backend then cleans the output so unsupported fields are removed before the frontend fills the form.

---

## CSV Export

CSV export is implemented in:

```text
api/tools/comps_export.py
```

`EXPORT_COMPS_CSV` uses the latest comps table already stored in the conversation state.

The export tool can:

- Export all latest comps.
- Export the top N comps.
- Export specific mentioned addresses from the latest comps table.

It reads full rows from:

```text
data/train/data.csv
```

The response includes:

- Export status
- Filename
- Row count
- Requested addresses
- Missing addresses
- Base64 CSV data URL
- Source path

---

## Conversation State

Conversation memory is implemented in:

```text
api/conversation_state.py
```

The backend stores state in an in-memory dictionary called `CONVERSATIONS`.

For each `conversation_id`, it tracks:

- Current subject property details
- Latest analysis result
- Recent chat messages

This lets the user ask follow-up questions such as:

```text
Why that price?
Explain the second comp.
Export the top 5.
```

The state is useful for a demo, but it is not persistent. Restarting the backend clears it.

---

## Trace Events

Trace events are implemented in:

```text
api/agent_debug.py
```

The backend records important steps such as:

- Request received
- Intent selected
- Tool called
- Tool returned
- Final answer created
- Fallback used

For `/chat/stream`, these trace events are sent to the frontend before the final response.

---

## Fallback Behavior

If Gemini fails because of an HTTP error, timeout, JSON parsing error, or similar backend issue, `build_response()` falls back to a simple answer.

If house details exist, it returns a backend error message.

If house details are missing, it asks the user to share property details first.

---

## Why This Agent Design Matters

The strongest part of this agent is that it separates language from computation.

Gemini handles:

- Intent detection
- Tool selection
- Follow-up question handling
- Final explanation writing
- PDF field extraction

Python handles:

- Model loading
- Price prediction
- Comp ranking
- SHAP-style price drivers
- LightGBM leaf comparison
- CSV export
- API response shape

This makes the system easier to trust. The final answer is conversational, but the numbers and comps come from the trained model and backend code.
