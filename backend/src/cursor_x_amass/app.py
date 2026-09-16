import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cursor_x_amass.analysis.schemas import AnalysisRequest, AnalysisResponse
from cursor_x_amass.analysis.service import analyze_idea

FRONTEND_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
)


def create_app() -> FastAPI:
    app = FastAPI(title="Research → Opportunity API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(FRONTEND_ORIGINS),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/analyze", response_model=AnalysisResponse)
    def analyze(payload: AnalysisRequest) -> AnalysisResponse:
        return analyze_idea(payload.idea)

    return app


def main() -> None:
    uvicorn.run(
        "cursor_x_amass.app:create_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
