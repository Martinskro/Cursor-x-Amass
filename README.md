# Research → Opportunity

Frontend and backend live in separate folders so two people can work without colliding.

## Layout

- `frontend/` — Vite UI (pages, styles, client)
- `backend/` — FastAPI API (analysis, Amass later)

## Who works where

To avoid merge conflicts, stay in your folder:

- UI / copy / layout → `frontend/`
- API / Amass analysis → `backend/`

The contract between you is `POST /api/analyze`. Frontend calls it from `frontend/src/api.js`. Backend implements it in `backend/src/cursor_x_amass/analysis/`.

## Run locally

Use two terminals.

Backend:

```bash
cd backend
uv sync
uv run cursor-x-amass
```

API: http://127.0.0.1:8000

Frontend:

```bash
cd frontend
npm install
npm run dev
```

App: http://127.0.0.1:5173

Vite proxies `/api` to the backend, so keep both processes running.
