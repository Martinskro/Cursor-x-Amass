from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from cursor_x_amass.analysis.schemas import AnalysisRequest, AnalysisResponse
from cursor_x_amass.analysis.service import analyze_idea

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"

EXAMPLE_IDEAS = [
    "Engineered yeast for sustainable production of specialty chemicals",
    "GLP-1 receptor agonists for metabolic and kidney disease",
    "CRISPR base editing for rare inherited metabolic disorders",
    "Inhaled mRNA therapeutics for lung inflammation",
]


def create_app() -> FastAPI:
    app = FastAPI(title="Research → Opportunity", version="0.1.0")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"examples": EXAMPLE_IDEAS},
        )

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
