from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.schemas import (
    ComparisonRequest,
    ComparisonResponse,
    GioiaAnalysisRequest,
    GioiaAnalysisResponse,
    HealthResponse,
    StudyCreate,
    StudyRecord,
    PersonaCreate,
    PersonaExtractRequest,
    PersonaRecord,
    QuestionExtractRequest,
    QuestionGuideCreate,
    QuestionGuideRecord,
    SimulationRequest,
    SimulationResponse,
    StudyProtocol,
    StudyProtocolCreate,
    TranscriptCreate,
    TranscriptRecord,
    UploadTextResponse,
)
from backend.services import ResearchBackendService
from backend.settings import settings
from backend.storage import get_storage


app = FastAPI(title=settings.api_title, version=settings.api_version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_service() -> ResearchBackendService:
    return ResearchBackendService(get_storage())


frontend_dir = Path("frontend")
if frontend_dir.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend")


def serve_frontend_page(filename: str):
    page_path = frontend_dir / filename
    if not page_path.exists():
        raise HTTPException(status_code=404, detail="Frontend page not found.")
    return FileResponse(page_path)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", storage_backend=settings.storage_backend)


for route_path, filename in {
    "/": "index.html",
    "/dashboard": "dashboard.html",
    "/studies": "studies.html",
    "/workspace": "workspace.html",
    "/protocol": "protocol.html",
    "/personas": "personas.html",
    "/interview-guide": "interview-guide.html",
    "/transcripts": "transcripts.html",
    "/simulations": "simulations.html",
    "/comparisons": "comparisons.html",
    "/settings": "settings.html",
    "/sign-in": "sign-in.html",
}.items():
    app.add_api_route(route_path, lambda filename=filename: serve_frontend_page(filename), include_in_schema=False)


@app.get("/api/studies", response_model=list[StudyRecord])
def list_studies(service: ResearchBackendService = Depends(get_service)):
    return service.list_collection("studies")


@app.post("/api/studies", response_model=StudyRecord)
def create_study(payload: StudyCreate, service: ResearchBackendService = Depends(get_service)):
    return service.save_study(payload.model_dump())


@app.get("/api/protocols", response_model=list[StudyProtocol])
def list_protocols(study_id: str | None = None, service: ResearchBackendService = Depends(get_service)):
    return service.list_collection("protocols", study_id=study_id)


@app.post("/api/protocols", response_model=StudyProtocol)
def create_protocol(payload: StudyProtocolCreate, service: ResearchBackendService = Depends(get_service)):
    return service.save_protocol(payload.model_dump())


@app.get("/api/personas", response_model=list[PersonaRecord])
def list_personas(study_id: str | None = None, service: ResearchBackendService = Depends(get_service)):
    return service.list_collection("personas", study_id=study_id)


@app.post("/api/personas", response_model=PersonaRecord)
def create_persona(payload: PersonaCreate, service: ResearchBackendService = Depends(get_service)):
    return service.save_persona(payload.model_dump())


@app.post("/api/personas/extract", response_model=PersonaRecord)
def extract_persona(payload: PersonaExtractRequest, service: ResearchBackendService = Depends(get_service)):
    persona = service.extract_persona(payload.text, payload.suggested_name)
    return service.save_persona(persona)


@app.post("/api/personas/extract-upload", response_model=UploadTextResponse)
async def extract_persona_upload(file: UploadFile = File(...), service: ResearchBackendService = Depends(get_service)):
    content = await file.read()
    text = service.extract_persona_text_from_upload(file.filename or "upload", file.content_type or "", content)
    return UploadTextResponse(text=text)


@app.post("/api/question-guides/extract", response_model=list[str])
def extract_questions(payload: QuestionExtractRequest, service: ResearchBackendService = Depends(get_service)):
    return service.extract_questions(payload.text, payload.improve_with_ai)


@app.post("/api/question-guides/extract-upload", response_model=UploadTextResponse)
async def extract_questions_upload(file: UploadFile = File(...), service: ResearchBackendService = Depends(get_service)):
    content = await file.read()
    text = service.extract_text_from_upload(file.filename or "upload", file.content_type or "", content)
    return UploadTextResponse(text=text)


@app.post("/api/question-guides", response_model=QuestionGuideRecord)
def create_question_guide(payload: QuestionGuideCreate, service: ResearchBackendService = Depends(get_service)):
    return service.save_question_guide(payload.name, payload.questions, payload.study_id)


@app.get("/api/question-guides", response_model=list[QuestionGuideRecord])
def list_question_guides(study_id: str | None = None, service: ResearchBackendService = Depends(get_service)):
    return service.list_collection("question_guides", study_id=study_id)


@app.post("/api/transcripts", response_model=TranscriptRecord)
def create_transcript(payload: TranscriptCreate, service: ResearchBackendService = Depends(get_service)):
    return service.save_transcript(payload.name, payload.content, payload.source_type, payload.study_id)


@app.post("/api/transcripts/extract-upload", response_model=UploadTextResponse)
async def extract_transcript_upload(file: UploadFile = File(...), service: ResearchBackendService = Depends(get_service)):
    content = await file.read()
    text = service.extract_text_from_upload(file.filename or "upload", file.content_type or "", content)
    return UploadTextResponse(text=text)


@app.get("/api/transcripts", response_model=list[TranscriptRecord])
def list_transcripts(study_id: str | None = None, service: ResearchBackendService = Depends(get_service)):
    return service.list_collection("transcripts", study_id=study_id)


@app.post("/api/simulations", response_model=SimulationResponse)
def create_simulation(payload: SimulationRequest, service: ResearchBackendService = Depends(get_service)):
    try:
        return service.run_simulation(payload.persona_id, payload.question_guide_id, payload.protocol_id, payload.study_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/simulations", response_model=list[SimulationResponse])
def list_simulations(study_id: str | None = None, service: ResearchBackendService = Depends(get_service)):
    return service.list_collection("simulations", study_id=study_id)


@app.post("/api/analyses/gioia", response_model=GioiaAnalysisResponse)
def create_gioia_analysis(payload: GioiaAnalysisRequest, service: ResearchBackendService = Depends(get_service)):
    try:
        return service.run_ai_gioia(payload.simulation_id, payload.protocol_id, payload.study_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/analyses/gioia", response_model=list[GioiaAnalysisResponse])
def list_gioia_analyses(study_id: str | None = None, service: ResearchBackendService = Depends(get_service)):
    return service.list_collection("gioia_analyses", study_id=study_id)


@app.post("/api/comparisons", response_model=ComparisonResponse)
def create_comparison(payload: ComparisonRequest, service: ResearchBackendService = Depends(get_service)):
    try:
        return service.run_structured_comparison(
            payload.transcript_id, payload.simulation_id, payload.protocol_id, payload.study_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/comparisons", response_model=list[ComparisonResponse])
def list_comparisons(study_id: str | None = None, service: ResearchBackendService = Depends(get_service)):
    return service.list_collection("comparisons", study_id=study_id)


@app.get("/api/simulations/{simulation_id}/exports/{file_type}")
def export_simulation(simulation_id: str, file_type: str, service: ResearchBackendService = Depends(get_service)):
    try:
        files = service.export_simulation(simulation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    path = files.get(file_type)
    if not path:
        raise HTTPException(status_code=404, detail="Export type not found.")
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Export file not found.")
    return FileResponse(file_path, filename=file_path.name)
