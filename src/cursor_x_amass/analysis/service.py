from cursor_x_amass.analysis.schemas import AnalysisResponse, AnalysisStatus


class AnalysisNotReadyError(Exception):
    """Raised until the Amass MCP analysis path is wired in."""


def analyze_idea(idea: str) -> AnalysisResponse:
    cleaned = idea.strip()
    if not cleaned:
        raise ValueError("Idea is required.")
    return AnalysisResponse(
        status=AnalysisStatus.NOT_IMPLEMENTED,
        idea=cleaned,
        message="Analysis is not connected yet. Amass cores will be queried from this service.",
    )
