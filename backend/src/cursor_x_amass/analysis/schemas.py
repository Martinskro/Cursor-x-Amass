from enum import StrEnum

from pydantic import BaseModel, Field


class AnalysisStatus(StrEnum):
    NOT_IMPLEMENTED = "not_implemented"


class AnalysisRequest(BaseModel):
    idea: str = Field(min_length=1, max_length=2000)


class AnalysisResponse(BaseModel):
    """Placeholder contract for the future Amass-backed pipeline.

    Cores the pipeline will call: BiomedCore, GeneCore, DrugCore,
    TrialCore, PatentCore, RegulatoryCore.
    """

    status: AnalysisStatus
    idea: str
    message: str
