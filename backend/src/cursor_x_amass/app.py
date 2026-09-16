from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from cursor_x_amass.investigation import store
from cursor_x_amass.investigation.schemas import (
    CoreIngestRequest,
    CreateInvestigationRequest,
    Investigation,
)
from cursor_x_amass.investigation.service import (
    InvestigationBusyError,
    cancel_investigation,
    ingest_core,
    start_investigation,
)

FRONTEND_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
)


def create_app() -> FastAPI:
    app = FastAPI(title="Licensa API", version="0.3.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(FRONTEND_ORIGINS),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/investigations/current", response_model=Investigation | None)
    def current_investigation() -> Investigation | None:
        return store.current()

    @app.post("/api/investigations", response_model=Investigation)
    def create_investigation_route(payload: CreateInvestigationRequest) -> Investigation:
        try:
            return start_investigation(payload.query)
        except InvestigationBusyError as exc:
            raise HTTPException(
                status_code=409,
                detail="An investigation is already running. Finish or cancel it first.",
            ) from exc

    @app.delete("/api/investigations/current")
    def delete_current_investigation() -> dict[str, str]:
        cancel_investigation()
        return {"status": "cancelled"}

    @app.get("/api/investigations/{job_id}", response_model=Investigation)
    def get_investigation(job_id: str) -> Investigation:
        job = store.current()
        if job is None or job.id != job_id:
            raise HTTPException(status_code=404, detail="Investigation not found.")
        return job

    @app.post("/api/investigations/{job_id}/cores/{core}", response_model=Investigation)
    def add_core_evidence(job_id: str, core: str, payload: CoreIngestRequest) -> Investigation:
        try:
            return ingest_core(job_id, core, payload)
        except KeyError:
            raise HTTPException(status_code=404, detail="Investigation not found.") from None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


def main() -> None:
    import uvicorn

    uvicorn.run(
        "cursor_x_amass.app:create_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
