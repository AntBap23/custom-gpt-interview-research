from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StudyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    description: str = ""


class StudyCreate(StudyBase):
    pass


class StudyRecord(StudyBase):
    id: str
    created_at: datetime
    updated_at: datetime


class StudyProtocolBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    shared_context: str = ""
    interview_style_guidance: str = ""
    consistency_rules: str = ""
    analysis_focus: str = ""


class StudyProtocolCreate(StudyProtocolBase):
    study_id: str | None = None
    pass


class StudyProtocol(StudyProtocolBase):
    id: str
    study_id: str | None = None
    created_at: datetime
    updated_at: datetime


class PersonaBase(BaseModel):
    name: str
    age: int | None = None
    job: str = "Professional"
    education: str = "Not specified"
    personality: str = "Not specified"
    original_text: str = ""
    opinions: dict[str, str] = Field(default_factory=dict)


class PersonaCreate(PersonaBase):
    study_id: str | None = None
    pass


class PersonaExtractRequest(BaseModel):
    text: str
    suggested_name: str | None = None


class PersonaRecord(PersonaBase):
    id: str
    study_id: str | None = None
    created_at: datetime
    updated_at: datetime


class QuestionExtractRequest(BaseModel):
    text: str
    improve_with_ai: bool = False


class QuestionGuideCreate(BaseModel):
    name: str
    questions: list[str]
    study_id: str | None = None


class QuestionGuideRecord(BaseModel):
    id: str
    name: str
    questions: list[str]
    study_id: str | None = None
    created_at: datetime
    updated_at: datetime


class TranscriptCreate(BaseModel):
    name: str
    content: str
    source_type: str = "text"
    study_id: str | None = None


class TranscriptRecord(BaseModel):
    id: str
    name: str
    content: str
    source_type: str = "text"
    study_id: str | None = None
    created_at: datetime
    updated_at: datetime


class SimulationRequest(BaseModel):
    persona_id: str
    question_guide_id: str
    protocol_id: str | None = None
    study_id: str | None = None


class SimulationResponse(BaseModel):
    id: str
    persona_id: str
    question_guide_id: str
    protocol_id: str | None = None
    study_id: str | None = None
    responses: list[dict[str, Any]]
    created_at: datetime


class GioiaAnalysisRequest(BaseModel):
    simulation_id: str
    protocol_id: str | None = None
    study_id: str | None = None


class GioiaAnalysisResponse(BaseModel):
    id: str
    simulation_id: str
    protocol_id: str | None = None
    study_id: str | None = None
    markdown: str
    created_at: datetime


class ComparisonRequest(BaseModel):
    transcript_id: str
    simulation_id: str
    protocol_id: str | None = None
    study_id: str | None = None


class ComparisonResponse(BaseModel):
    id: str
    transcript_id: str
    simulation_id: str
    protocol_id: str | None = None
    study_id: str | None = None
    payload: dict[str, Any]
    created_at: datetime


class UploadTextResponse(BaseModel):
    text: str


class HealthResponse(BaseModel):
    status: str
    storage_backend: str
