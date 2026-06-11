# Frontend

This is the Next.js chat interface for Housing AI Agent. It lets users create a subject-property conversation, stream backend agent events, inspect valuation/comps results, parse property PDFs, and export comps as CSV.

## Setup

Install dependencies:

```powershell
npm install
```

Run the development server:

```powershell
npm run dev
```

Open:

```text
http://localhost:3000
```

The backend must also be running at:

```text
http://localhost:8000
```

## Key Files

- `app/page.tsx`: full-screen application shell.
- `components/AgentChat.tsx`: conversation state, streaming chat call, CSV export handling.
- `components/HouseDetailsForm.tsx`: subject-property form and PDF extraction flow.
- `components/agent-chat/`: chat header, input, message list, result cards, and shared types.

## Scripts

```powershell
npm run dev
npm run build
npm run start
npm run lint
```

## Backend Contract

The frontend sends chat requests to `POST /chat/stream` and expects newline-delimited JSON events:

```json
{ "type": "trace", "event": { "phase": "tool", "message": "Calling GET_COMPS" } }
{ "type": "final", "response": { "answer": "...", "comps": [] } }
```

See `../docs/API.md` for the full API reference.
