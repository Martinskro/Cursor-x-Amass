# Licensa

Find the science. Find the IP. Find the opportunity.

Frontend and backend live in separate folders so two people can work without colliding.

## Layout

- `frontend/` — Vite UI (homepage, investigation views)
- `backend/` — FastAPI investigation jobs; Amass MCP fills each core

## Who works where

- UI / copy / layout → `frontend/`
- Investigation / Amass → `backend/`

## Run locally

Frontend:

```bash
cd frontend
npm install
npm run dev
```

App: http://127.0.0.1:5173

Keep both running for investigation. The UI polls `/api/investigations`; Amass MCP results are ingested per core.

Backend:

```bash
cd backend
uv sync
uv run cursor-x-amass
```

API: http://127.0.0.1:8000
