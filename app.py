import csv
import io
import json
import logging
import re
from pathlib import Path
from typing import Any

import openai
import nicegui.run as nicegui_run
from nicegui import ui

from config import get_secret
from scripts.analyze_gioia import analyze_gioia
from scripts.export_results import export_all_formats
from scripts.simulate_interviews import simulate_interview
from utils.docx_parser import extract_questions_from_docx, extract_text_from_docx
from utils.pdf_parser import (
    extract_questions_with_ai,
    extract_text_from_pdf,
    validate_and_improve_questions,
)
from utils.persona_parser import (
    extract_persona_info_with_ai,
    extract_text_from_pdf_persona,
    validate_persona_data,
)
from utils.txt_parser import extract_questions_from_txt, extract_text_from_txt


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def safe_nicegui_setup() -> None:
    """Allow NiceGUI to run in restricted environments where process semaphores are unavailable."""
    try:
        nicegui_run.process_pool = nicegui_run.ProcessPoolExecutor()
    except (NotImplementedError, PermissionError):
        logger.warning("NiceGUI process pool is unavailable; continuing without cpu_bound support.")


nicegui_run.setup = safe_nicegui_setup

APP_DIRS = ["personas", "data", "data/ai_responses", "outputs", "questions", "exports", "study_protocols"]
QUESTIONS_PATH = Path("questions/questions.txt")
REAL_TRANSCRIPT_PATH = Path("data/real_interview_transcript.txt")
PERSONAS_DIR = Path("personas")
AI_RESPONSES_DIR = Path("data/ai_responses")
OUTPUTS_DIR = Path("outputs")
EXPORTS_DIR = Path("exports")
STUDY_PROTOCOLS_DIR = Path("study_protocols")

for dir_path in APP_DIRS:
    Path(dir_path).mkdir(parents=True, exist_ok=True)


state: dict[str, Any] = {
    "questions": None,
    "study_settings": None,
    "manual_persona_data": None,
    "manual_persona_text": "",
    "latest_comparison": "",
    "latest_comparison_structured": None,
    "latest_real_analysis": "",
    "latest_ai_analysis": "",
}


def default_study_settings() -> dict[str, Any]:
    return {
        "protocol_name": "niu-research-protocol",
        "model": "gpt-4o-mini",
        "temperature": 0.55,
        "analysis_temperature": 0.3,
        "max_answer_tokens": 500,
        "analysis_max_tokens": 2200,
        "quote_count": 4,
        "coding_depth": "Standard",
        "shared_context": (
            "This study investigates AI-generated personas as methodological augments that improve "
            "research design, reflexivity, and validity checking without replacing human participants."
        ),
        "interview_style": (
            "Answer like a real participant in a qualitative interview. Use concrete language, include tensions and "
            "partial uncertainty, and avoid sounding like a polished summary report."
        ),
        "consistency_rules": (
            "Stay consistent with the persona across the whole interview. Do not drift toward generic or overly tidy answers."
        ),
        "analysis_focus": (
            "Pay special attention to protocol refinement, researcher reflexivity, validity checking, emotional nuance, "
            "contextual specificity, and whether AI responses become too abstract."
        ),
    }


state["study_settings"] = default_study_settings()


def safe_read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_questions() -> list[str]:
    if not QUESTIONS_PATH.exists():
        return []
    return [line.strip() for line in QUESTIONS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def save_questions(questions: list[str]) -> None:
    QUESTIONS_PATH.write_text("\n".join(questions), encoding="utf-8")
    state["questions"] = questions


def save_transcript(text: str) -> None:
    REAL_TRANSCRIPT_PATH.write_text(text, encoding="utf-8")


def get_persona_files() -> list[Path]:
    return sorted(PERSONAS_DIR.glob("*.json"))


def get_ai_response_files() -> list[Path]:
    return sorted(AI_RESPONSES_DIR.glob("*.json"))


def get_protocol_files() -> list[Path]:
    return sorted(STUDY_PROTOCOLS_DIR.glob("*.json"))


def load_persona(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_persona(persona_data: dict[str, Any]) -> Path:
    validated = validate_persona_data(persona_data)
    slug = re.sub(r"[^a-z0-9]+", "_", validated["name"].strip().lower()).strip("_") or "persona"
    path = PERSONAS_DIR / f"{slug}.json"
    path.write_text(json.dumps(validated, indent=2), encoding="utf-8")
    return path


def load_ai_interview(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_protocol(settings: dict[str, Any]) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "_", settings.get("protocol_name", "study-protocol").strip().lower()).strip("_")
    path = STUDY_PROTOCOLS_DIR / f"{slug or 'study_protocol'}.json"
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return path


def extract_json_payload(raw_text: str) -> dict[str, Any] | None:
    if not raw_text:
        return None
    text = raw_text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def save_structured_comparison(base_name: str, payload: dict[str, Any]) -> dict[str, Path]:
    json_path = OUTPUTS_DIR / f"{base_name}.json"
    md_path = OUTPUTS_DIR / f"{base_name}.md"
    csv_path = OUTPUTS_DIR / f"{base_name}.csv"
    html_path = OUTPUTS_DIR / f"{base_name}.html"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(payload.get("markdown_report", ""), encoding="utf-8")

    rows = payload.get("comparison_table", [])
    with open(csv_path, "w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=["theme", "real_pattern", "ai_pattern", "difference", "research_implication"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    html_parts = [
        "<html><head><meta charset='utf-8'><title>Structured Comparison</title></head><body>",
        "<h1>Structured Comparison</h1>",
        f"<p>{payload.get('overview', {}).get('key_takeaway', '')}</p>",
        "<table border='1' cellpadding='8' cellspacing='0'>",
        "<tr><th>Theme</th><th>Real Pattern</th><th>AI Pattern</th><th>Difference</th><th>Research Implication</th></tr>",
    ]
    for row in rows:
        html_parts.append(
            "<tr>"
            f"<td>{row.get('theme', '')}</td>"
            f"<td>{row.get('real_pattern', '')}</td>"
            f"<td>{row.get('ai_pattern', '')}</td>"
            f"<td>{row.get('difference', '')}</td>"
            f"<td>{row.get('research_implication', '')}</td>"
            "</tr>"
        )
    html_parts.append("</table></body></html>")
    html_path.write_text("\n".join(html_parts), encoding="utf-8")

    return {"json": json_path, "md": md_path, "csv": csv_path, "html": html_path}


def save_markdown(path: Path, title: str, body: str) -> None:
    path.write_text(f"# {title}\n\n{body}", encoding="utf-8")


def bytes_to_buffer(content: bytes, name: str) -> io.BytesIO:
    buffer = io.BytesIO(content)
    buffer.name = name
    return buffer


def notify_error(message: str, exc: Exception | None = None) -> None:
    logger.exception(message, exc_info=exc) if exc else logger.error(message)
    ui.notify(message, type="negative")


def current_questions() -> list[str]:
    if state["questions"] is None:
        state["questions"] = load_questions()
    return state["questions"] or []


def get_client() -> openai.OpenAI:
    api_key = get_secret("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    return openai.OpenAI(api_key=api_key)


def run_comparison(ai_file: Path) -> str:
    real_transcript = safe_read_text(REAL_TRANSCRIPT_PATH)
    ai_responses = load_ai_interview(ai_file)
    ai_text = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in ai_responses])
    settings = state["study_settings"]

    comparison_prompt = f"""
    You are supporting a qualitative research project comparing real interviews to AI-simulated persona interviews.

    The study logic is:
    - same interview guide
    - persona-conditioned AI responses
    - comparison of where AI aligns, over-structures, misses nuance, or becomes generic
    - additional protocol focus: {settings.get("analysis_focus", "")}

    Please produce a structured markdown analysis with these sections:
    1. Snapshot of the real interview and the AI interview
    2. First-order concepts with representative quotes from both datasets
    3. Second-order themes
    4. Aggregate dimensions
    5. A side-by-side matrix for Real vs AI
    6. Research implications, including where AI may be useful as an augmentative tool and where it falls short

    Real interview transcript:
    {real_transcript[:5000]}

    AI-generated interview:
    {ai_text[:5000]}
    """

    response = get_client().chat.completions.create(
        model=settings.get("model", "gpt-4o-mini"),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert qualitative researcher using Gioia-style analysis. "
                    "Be concrete, comparative, and skeptical of overly polished AI responses."
                ),
            },
            {"role": "user", "content": comparison_prompt},
        ],
        max_tokens=settings.get("analysis_max_tokens", 2200),
        temperature=settings.get("analysis_temperature", 0.3),
    )
    return response.choices[0].message.content or ""


def run_structured_comparison(ai_file: Path) -> dict[str, Any] | None:
    real_transcript = safe_read_text(REAL_TRANSCRIPT_PATH)
    ai_responses = load_ai_interview(ai_file)
    ai_text = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in ai_responses])
    settings = state["study_settings"]

    prompt = f"""
    Compare a real interview transcript against an AI-generated interview and return valid JSON only.

    Use this structure exactly:
    {{
      "overview": {{
        "real_summary": "...",
        "ai_summary": "...",
        "key_takeaway": "..."
      }},
      "comparison_table": [
        {{
          "theme": "...",
          "real_pattern": "...",
          "ai_pattern": "...",
          "difference": "...",
          "research_implication": "..."
        }}
      ],
      "quotes": {{
        "real": [
          {{"theme": "...", "quote": "...", "why_it_matters": "..."}}
        ],
        "ai": [
          {{"theme": "...", "quote": "...", "why_it_matters": "..."}}
        ]
      }},
      "theme_review": [
        {{
          "dimension": "...",
          "theme": "...",
          "first_order_concepts": ["...", "..."],
          "real_evidence": "...",
          "ai_evidence": "...",
          "review_note": "..."
        }}
      ],
      "markdown_report": "..."
    }}

    Requirements:
    - Include 4 to 6 comparison themes.
    - Include up to {settings.get("quote_count", 4)} real quotes and up to {settings.get("quote_count", 4)} AI quotes.
    - Focus on qualitative differences in specificity, emotional texture, lived context, and genericity.
    - Additional analysis focus: {settings.get("analysis_focus", "")}

    Real transcript:
    {real_transcript[:6000]}

    AI transcript:
    {ai_text[:6000]}
    """

    response = get_client().chat.completions.create(
        model=settings.get("model", "gpt-4o-mini"),
        messages=[
            {
                "role": "system",
                "content": "You are an expert qualitative researcher. Return valid JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=settings.get("analysis_max_tokens", 2200),
        temperature=settings.get("analysis_temperature", 0.3),
    )
    return extract_json_payload(response.choices[0].message.content or "")


def run_real_interview_analysis() -> str:
    real_transcript = safe_read_text(REAL_TRANSCRIPT_PATH)
    settings = state["study_settings"]
    prompt = f"""
    Analyze this real interview transcript using Gioia methodology.
    Return markdown with:
    - 3 aggregate dimensions
    - 2 to 4 themes per dimension
    - 3 to 5 first-order concepts per theme
    - representative quotes
    - a short memo on what is especially human, contextual, or surprising in the transcript
    - additional analysis focus: {settings.get("analysis_focus", "")}

    Transcript:
    {real_transcript[:6000]}
    """
    response = get_client().chat.completions.create(
        model=settings.get("model", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "You are an expert qualitative researcher using the Gioia methodology."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=settings.get("analysis_max_tokens", 2200),
        temperature=settings.get("analysis_temperature", 0.3),
    )
    return response.choices[0].message.content or ""


def metric_card(label: str, value: str) -> None:
    with ui.card().classes("metric-card"):
        ui.label(label).classes("metric-label")
        ui.label(value).classes("metric-value")


def persona_card(persona_path: Path) -> None:
    persona = load_persona(persona_path)
    opinions = persona.get("opinions", {})
    age = persona.get("age") if persona.get("age") is not None else "Age not specified"
    with ui.card().classes("persona-card"):
        ui.label(persona.get("name", persona_path.stem)).classes("persona-name")
        ui.label(f"{persona.get('job', 'Role not specified')} • {age}").classes("persona-meta")
        ui.markdown(f"**Education**  \n{persona.get('education', 'Not specified')}")
        ui.markdown(f"**Personality**  \n{persona.get('personality', 'Not specified')}")
        ui.markdown(f"**AI Stance**  \n{opinions.get('AI', 'Not specified')}")


def refresh_page() -> None:
    ui.navigate.reload()


def handle_transcript_upload(event) -> None:
    try:
        content = event.content.read()
        name = event.name
        suffix = Path(name).suffix.lower()
        if suffix == ".pdf":
            text = extract_text_from_pdf(bytes_to_buffer(content, name))
        elif suffix == ".docx":
            text = extract_text_from_docx(bytes_to_buffer(content, name))
        else:
            text = extract_text_from_txt(bytes_to_buffer(content, name))
        if not text.strip():
            ui.notify("Could not extract text from the transcript file.", type="warning")
            return
        save_transcript(text)
        ui.notify("Transcript loaded.", type="positive")
        refresh_page()
    except Exception as exc:
        notify_error("Transcript upload failed.", exc)


def handle_questions_upload(event) -> None:
    try:
        content = event.content.read()
        name = event.name
        suffix = Path(name).suffix.lower()
        if suffix == ".pdf":
            text = extract_text_from_pdf(bytes_to_buffer(content, name))
            questions = extract_questions_with_ai(text)
        elif suffix == ".docx":
            questions = extract_questions_from_docx(bytes_to_buffer(content, name))
        else:
            questions = extract_questions_from_txt(bytes_to_buffer(content, name))
        if not questions:
            ui.notify("No questions were extracted from that file.", type="warning")
            return
        save_questions(questions)
        ui.notify(f"Loaded {len(questions)} interview questions.", type="positive")
        refresh_page()
    except Exception as exc:
        notify_error("Question upload failed.", exc)


def build_ui() -> None:
    ui.add_head_html(
        """
        <style>
            body { background:
                radial-gradient(circle at 10% 0%, rgba(15, 98, 83, 0.14), transparent 25%),
                radial-gradient(circle at 100% 10%, rgba(201, 113, 60, 0.18), transparent 30%),
                linear-gradient(180deg, #f7f2e9 0%, #efe7da 100%);
                color: #1f1d1a;
            }
            .app-shell { max-width: 1440px; margin: 0 auto; padding: 24px 18px 48px; }
            .hero-card, .section-card, .metric-card, .persona-card, .table-card, .analysis-card {
                background: rgba(255, 250, 244, 0.86);
                border: 1px solid rgba(90, 72, 44, 0.12);
                box-shadow: 0 18px 50px rgba(55, 43, 28, 0.08);
                backdrop-filter: blur(10px);
            }
            .hero-card { border-radius: 30px; padding: 22px; }
            .kicker { color: #0f6253; text-transform: uppercase; letter-spacing: .18em; font-size: .75rem; font-weight: 700; }
            .hero-title { font-size: 3.4rem; line-height: .92; font-weight: 800; max-width: 760px; margin: 10px 0 14px; }
            .hero-copy { max-width: 900px; color: #5a534a; font-size: 1rem; line-height: 1.7; }
            .metric-card { border-radius: 22px; padding: 16px; min-height: 112px; }
            .metric-label { text-transform: uppercase; letter-spacing: .14em; font-size: .72rem; color: #6f665b; font-weight: 700; }
            .metric-value { font-size: 1.55rem; font-weight: 800; margin-top: 10px; }
            .section-title { font-size: 1.25rem; font-weight: 800; }
            .section-note { color: #60574d; line-height: 1.6; }
            .persona-card { border-radius: 22px; padding: 16px; min-height: 220px; }
            .persona-name { font-size: 1.1rem; font-weight: 800; }
            .persona-meta { color: #6c645b; margin-bottom: 8px; }
            .research-note {
                background: rgba(201, 113, 60, 0.10);
                border-left: 4px solid #c9713c;
                border-radius: 16px;
                padding: 14px 16px;
                color: #503a2f;
            }
            .pill { background: rgba(15, 98, 83, 0.10); color: #0f6253; border-radius: 999px; padding: 6px 10px; font-weight: 700; font-size: .8rem; }
            .tab-panel { padding-top: 18px; }
        </style>
        """
    )

    with ui.element("div").classes("app-shell"):
        with ui.card().classes("hero-card w-full"):
            ui.label("Qualitative Research Workflow").classes("kicker")
            ui.label("A research studio for comparing human interviews with AI-generated personas.").classes("hero-title")
            ui.label(
                "This frontend is built for researchers who need a cleaner workflow: load a shared interview guide, "
                "create grounded personas, simulate interviews, and compare AI output against real transcript material "
                "with protocol refinement, reflexivity, and validity checking in view."
            ).classes("hero-copy")

        with ui.row().classes("w-full q-col-gutter-lg q-mt-lg"):
            metric_card("Research Guide", f"{len(current_questions())} questions" if current_questions() else "Not loaded")
            metric_card("Personas", str(len(get_persona_files())))
            metric_card("AI Interviews", str(len(get_ai_response_files())))
            metric_card("Real Transcript", "Ready" if REAL_TRANSCRIPT_PATH.exists() else "Missing")

        with ui.row().classes("w-full q-col-gutter-xl q-mt-lg items-start"):
            with ui.column().classes("col-12 col-md-8"):
                tabs = ui.tabs().classes("w-full")
                study_tab = ui.tab("Study Design")
                persona_tab = ui.tab("Persona Studio")
                simulation_tab = ui.tab("Simulation Lab")
                analysis_tab = ui.tab("Analysis Studio")

                with ui.tab_panels(tabs, value=study_tab).classes("w-full bg-transparent"):
                    with ui.tab_panel(study_tab).classes("tab-panel"):
                        render_study_design()
                    with ui.tab_panel(persona_tab).classes("tab-panel"):
                        render_persona_studio()
                    with ui.tab_panel(simulation_tab).classes("tab-panel"):
                        render_simulation_lab()
                    with ui.tab_panel(analysis_tab).classes("tab-panel"):
                        render_analysis_studio()

            with ui.column().classes("col-12 col-md-4"):
                render_sidebar()


def render_sidebar() -> None:
    with ui.card().classes("section-card w-full q-pa-lg"):
        ui.label("Research Fit").classes("section-title")
        ui.label(
            "Designed around the NIU-style paired interview workflow: same guide, persona-conditioned AI responses, "
            "and explicit review of where AI becomes too clean, abstract, or context-thin."
        ).classes("section-note")
        with ui.column().classes("q-gutter-sm q-mt-md"):
            for text in [
                "Use one shared guide across human and simulated interviews.",
                "Keep personas specific enough to avoid generic responses.",
                "Compare whole-interview patterns, not only isolated answers.",
                "Treat AI as methodological augmentation, not a participant substitute.",
            ]:
                ui.label(text).classes("section-note")

    with ui.card().classes("section-card w-full q-pa-lg q-mt-md"):
        ui.label("Study Progress").classes("section-title")
        for label, ready in [
            ("Real transcript loaded", REAL_TRANSCRIPT_PATH.exists()),
            ("Interview guide loaded", bool(current_questions())),
            ("Personas prepared", bool(get_persona_files())),
            ("Simulations generated", bool(get_ai_response_files())),
        ]:
            with ui.row().classes("w-full justify-between items-center q-my-xs"):
                ui.label(label).classes("section-note")
                ui.badge("Ready" if ready else "Waiting", color="positive" if ready else "grey-6")

    with ui.card().classes("section-card w-full q-pa-lg q-mt-md"):
        ui.label("Environment").classes("section-title")
        api_ready = bool(get_secret("OPENAI_API_KEY"))
        ui.badge("API key detected" if api_ready else "Missing OPENAI_API_KEY", color="positive" if api_ready else "negative")
        ui.label("The app relies on local files, so it is best suited to individual or pilot research use.").classes("section-note q-mt-sm")


def render_study_design() -> None:
    settings = state["study_settings"]
    transcript_preview = safe_read_text(REAL_TRANSCRIPT_PATH)
    questions = current_questions()

    with ui.card().classes("section-card w-full q-pa-lg"):
        ui.label("Study Design").classes("section-title")
        ui.label(
            "Start with the real transcript and the shared interview guide. Better comparability starts with stronger protocol discipline."
        ).classes("section-note")
        ui.upload(
            on_upload=handle_transcript_upload,
            label="Upload real interview transcript (.txt, .docx, .pdf)",
            auto_upload=True,
        ).props("accept=.txt,.docx,.pdf").classes("w-full q-mt-md")
        if transcript_preview:
            ui.textarea(label="Transcript preview", value=transcript_preview[:3500]).props("readonly autogrow").classes("w-full q-mt-md")

    with ui.card().classes("section-card w-full q-pa-lg q-mt-md"):
        ui.label("Interview Guide").classes("section-title")
        ui.upload(
            on_upload=handle_questions_upload,
            label="Upload interview guide (.txt, .docx, .pdf)",
            auto_upload=True,
        ).props("accept=.txt,.docx,.pdf").classes("w-full q-mt-md")
        questions_editor = ui.textarea(
            label="Review and refine the guide",
            value="\n".join(questions),
        ).props("autogrow").classes("w-full q-mt-md")

        def save_edited_questions() -> None:
            revised = [line.strip() for line in questions_editor.value.splitlines() if line.strip()]
            save_questions(revised)
            ui.notify(f"Saved {len(revised)} questions.", type="positive")
            refresh_page()

        def polish_questions() -> None:
            try:
                revised = [line.strip() for line in questions_editor.value.splitlines() if line.strip()]
                improved = validate_and_improve_questions(revised)
                if improved:
                    save_questions(improved)
                    ui.notify("Question guide improved and saved.", type="positive")
                    refresh_page()
            except Exception as exc:
                notify_error("Question polishing failed.", exc)

        with ui.row().classes("q-gutter-md q-mt-md"):
            ui.button("Save question guide", on_click=save_edited_questions, color="primary")
            ui.button("Polish questions with AI", on_click=polish_questions, color="secondary")

    with ui.card().classes("section-card w-full q-pa-lg q-mt-md"):
        ui.label("Study Protocol").classes("section-title")
        protocol_name = ui.input("Protocol name", value=settings["protocol_name"]).classes("w-full")
        shared_context = ui.textarea("Shared study context", value=settings["shared_context"]).props("autogrow").classes("w-full")
        interview_style = ui.textarea("Interview style guidance", value=settings["interview_style"]).props("autogrow").classes("w-full")
        consistency_rules = ui.textarea("Consistency rules", value=settings["consistency_rules"]).props("autogrow").classes("w-full")
        analysis_focus = ui.textarea("Analysis focus", value=settings["analysis_focus"]).props("autogrow").classes("w-full")

        with ui.row().classes("w-full q-col-gutter-md"):
            model_input = ui.input("Model", value=settings["model"]).classes("col")
            temperature = ui.number("Simulation temperature", value=settings["temperature"], min=0, max=2, step=0.05).classes("col")
            analysis_temperature = ui.number("Analysis temperature", value=settings["analysis_temperature"], min=0, max=2, step=0.05).classes("col")
        with ui.row().classes("w-full q-col-gutter-md"):
            max_answer_tokens = ui.number("Max answer tokens", value=settings["max_answer_tokens"], min=100, step=50).classes("col")
            analysis_max_tokens = ui.number("Analysis max tokens", value=settings["analysis_max_tokens"], min=500, step=100).classes("col")
            quote_count = ui.number("Quote count", value=settings["quote_count"], min=1, max=10, step=1).classes("col")
        coding_depth = ui.select(["Light", "Standard", "Deep"], value=settings["coding_depth"], label="Coding depth").classes("w-64")

        def collect_settings() -> dict[str, Any]:
            return {
                "protocol_name": protocol_name.value,
                "model": model_input.value,
                "temperature": temperature.value,
                "analysis_temperature": analysis_temperature.value,
                "max_answer_tokens": int(max_answer_tokens.value),
                "analysis_max_tokens": int(analysis_max_tokens.value),
                "quote_count": int(quote_count.value),
                "coding_depth": coding_depth.value,
                "shared_context": shared_context.value,
                "interview_style": interview_style.value,
                "consistency_rules": consistency_rules.value,
                "analysis_focus": analysis_focus.value,
            }

        def apply_protocol() -> None:
            state["study_settings"] = collect_settings()
            ui.notify("Protocol settings applied.", type="positive")

        def persist_protocol() -> None:
            settings_payload = collect_settings()
            state["study_settings"] = settings_payload
            saved_path = save_protocol(settings_payload)
            ui.notify(f"Saved protocol to {saved_path.name}.", type="positive")
            refresh_page()

        def reset_protocol() -> None:
            state["study_settings"] = default_study_settings()
            ui.notify("Protocol reset.", type="positive")
            refresh_page()

        with ui.row().classes("q-gutter-md q-mt-md"):
            ui.button("Apply protocol settings", on_click=apply_protocol, color="primary")
            ui.button("Save protocol", on_click=persist_protocol, color="secondary")
            ui.button("Reset protocol", on_click=reset_protocol, color="accent")


def render_persona_studio() -> None:
    persona_files = get_persona_files()
    with ui.card().classes("section-card w-full q-pa-lg"):
        ui.label("Persona Studio").classes("section-title")
        ui.label(
            "Build respondents with enough lived context to make the AI interview analytically useful. Thin personas produce thin transcripts."
        ).classes("section-note")
        if persona_files:
            with ui.grid(columns=3).classes("w-full q-mt-md"):
                for persona_path in persona_files:
                    persona_card(persona_path)
        else:
            ui.label("No personas saved yet.").classes("section-note q-mt-md")

    with ui.card().classes("section-card w-full q-pa-lg q-mt-md"):
        ui.label("Create Persona").classes("section-title")
        mode = ui.toggle(["Manual narrative", "Upload source document"], value="Manual narrative").classes("q-mb-md")
        manual_box = ui.textarea(
            label="Persona narrative",
            value=state["manual_persona_text"],
            placeholder="Describe role, context, values, tensions, and how this person thinks about the focal topic.",
        ).props("autogrow").classes("w-full")

        upload_wrap = ui.column().classes("w-full")
        upload_wrap.set_visibility(False)

        def switch_mode() -> None:
            is_manual = mode.value == "Manual narrative"
            manual_box.set_visibility(is_manual)
            upload_wrap.set_visibility(not is_manual)

        mode.on_value_change(lambda _: switch_mode())

        extracted_wrap = ui.column().classes("w-full q-mt-md")

        def show_extracted_persona(persona_data: dict[str, Any]) -> None:
            extracted_wrap.clear()
            with extracted_wrap:
                ui.separator()
                ui.label("Review extracted persona").classes("section-title q-mt-md")
                with ui.row().classes("w-full q-col-gutter-md"):
                    name = ui.input("Name", value=persona_data["name"]).classes("col")
                    age = ui.number("Age", value=persona_data.get("age") or 0, min=0, max=120, step=1).classes("col")
                    job = ui.input("Role / profession", value=persona_data["job"]).classes("col")
                education = ui.input("Education", value=persona_data["education"]).classes("w-full")
                personality = ui.textarea("Personality and disposition", value=persona_data["personality"]).props("autogrow").classes("w-full")
                ai_opinion = ui.input("Opinion on AI / technology", value=persona_data.get("opinions", {}).get("AI", "Not specified")).classes("w-full")
                remote_opinion = ui.input("Opinion on remote work", value=persona_data.get("opinions", {}).get("Remote Work", "Not specified")).classes("w-full")

                def persist_persona() -> None:
                    saved = save_persona(
                        {
                            "name": name.value,
                            "age": None if int(age.value or 0) == 0 else int(age.value),
                            "job": job.value,
                            "education": education.value,
                            "personality": personality.value,
                            "original_text": persona_data.get("original_text", state["manual_persona_text"]),
                            "opinions": {"AI": ai_opinion.value, "Remote Work": remote_opinion.value},
                        }
                    )
                    state["manual_persona_data"] = None
                    state["manual_persona_text"] = ""
                    ui.notify(f"Saved persona to {saved.name}.", type="positive")
                    refresh_page()

                ui.button("Save persona", on_click=persist_persona, color="primary").classes("q-mt-md")

        def extract_manual_persona() -> None:
            try:
                if not manual_box.value.strip():
                    ui.notify("Add a persona narrative first.", type="warning")
                    return
                state["manual_persona_text"] = manual_box.value
                persona_counter = len(persona_files) + 1
                persona_data = extract_persona_info_with_ai(manual_box.value, persona_counter)
                state["manual_persona_data"] = persona_data
                show_extracted_persona(persona_data)
            except Exception as exc:
                notify_error("Persona extraction failed.", exc)

        def clear_persona_draft() -> None:
            state["manual_persona_data"] = None
            state["manual_persona_text"] = ""
            refresh_page()

        with ui.row().classes("q-gutter-md q-mt-md"):
            ui.button("Extract persona", on_click=extract_manual_persona, color="primary")
            ui.button("Clear draft", on_click=clear_persona_draft, color="secondary")

        with upload_wrap:
            def handle_persona_upload(event) -> None:
                try:
                    content = event.content.read()
                    suffix = Path(event.name).suffix.lower()
                    if suffix == ".pdf":
                        document_text = extract_text_from_pdf_persona(bytes_to_buffer(content, event.name))
                    elif suffix == ".docx":
                        document_text = extract_text_from_docx(bytes_to_buffer(content, event.name))
                    else:
                        document_text = extract_text_from_txt(bytes_to_buffer(content, event.name))
                    if not document_text.strip():
                        ui.notify("Could not extract text from the persona document.", type="warning")
                        return
                    state["manual_persona_text"] = document_text
                    persona_counter = len(persona_files) + 1
                    persona_data = extract_persona_info_with_ai(document_text, persona_counter)
                    state["manual_persona_data"] = persona_data
                    show_extracted_persona(persona_data)
                except Exception as exc:
                    notify_error("Persona document processing failed.", exc)

            ui.upload(
                on_upload=handle_persona_upload,
                label="Upload persona source (.txt, .docx, .pdf)",
                auto_upload=True,
            ).props("accept=.txt,.docx,.pdf").classes("w-full")

        if state.get("manual_persona_data"):
            show_extracted_persona(state["manual_persona_data"])


def render_simulation_lab() -> None:
    questions = current_questions()
    persona_files = get_persona_files()
    ai_files = get_ai_response_files()

    with ui.card().classes("section-card w-full q-pa-lg"):
        ui.label("Simulation Lab").classes("section-title")
        ui.label(
            "Generate persona-based interviews and inspect whether the transcripts actually feel distinct instead of merely coherent."
        ).classes("section-note")
        with ui.row().classes("q-gutter-md q-mt-md"):
            ui.badge(f"{len(questions)} questions" if questions else "No question guide", color="positive" if questions else "negative")
            ui.badge(f"{len(persona_files)} personas", color="positive" if persona_files else "negative")
            ui.badge(f"{len(ai_files)} AI interviews", color="primary")

        if not questions:
            ui.label("Load the interview guide in Study Design before running simulations.").classes("research-note q-mt-md")
            return
        if not persona_files:
            ui.label("Create at least one persona in Persona Studio before running simulations.").classes("research-note q-mt-md")
            return

        selected_personas = ui.select(
            options={path.name: path.stem.replace("_", " ").title() for path in persona_files},
            value=[path.name for path in persona_files],
            with_input=False,
            multiple=True,
            label="Choose personas to simulate",
        ).classes("w-full q-mt-md")

        def simulate_many(paths: list[Path]) -> None:
            try:
                if not paths:
                    ui.notify("Choose at least one persona.", type="warning")
                    return
                for persona_path in paths:
                    output_path = AI_RESPONSES_DIR / f"{persona_path.stem}_responses.json"
                    simulate_interview(str(persona_path), str(QUESTIONS_PATH), str(output_path), settings=state["study_settings"])
                ui.notify(f"Generated {len(paths)} AI interview(s).", type="positive")
                refresh_page()
            except Exception as exc:
                notify_error("Simulation failed.", exc)

        with ui.row().classes("q-gutter-md q-mt-md"):
            ui.button(
                "Run selected simulations",
                on_click=lambda: simulate_many([PERSONAS_DIR / name for name in (selected_personas.value or [])]),
                color="primary",
            )
            ui.button(
                "Run missing simulations only",
                on_click=lambda: simulate_many(
                    [
                        path
                        for path in persona_files
                        if not (AI_RESPONSES_DIR / f"{path.stem}_responses.json").exists()
                    ]
                ),
                color="secondary",
            )

        rows = [
            {
                "persona": path.stem.replace("_", " ").title(),
                "status": "Ready" if (AI_RESPONSES_DIR / f"{path.stem}_responses.json").exists() else "Not run",
            }
            for path in persona_files
        ]
        ui.table(
            columns=[
                {"name": "persona", "label": "Persona", "field": "persona", "align": "left"},
                {"name": "status", "label": "Status", "field": "status", "align": "left"},
            ],
            rows=rows,
        ).classes("w-full q-mt-md")

        if ai_files:
            preview_select = ui.select(
                options={path.name: path.stem.replace("_", " ").title() for path in ai_files},
                value=ai_files[0].name,
                label="Preview AI interview",
            ).classes("w-full q-mt-md")
            preview_box = ui.markdown().classes("w-full q-mt-md")

            def update_preview() -> None:
                selected = AI_RESPONSES_DIR / preview_select.value
                interview = load_ai_interview(selected)
                chunks = []
                for item in interview[:5]:
                    chunks.append(f"### Q: {item['question']}\n\n{item['answer']}")
                preview_box.set_content("\n\n---\n\n".join(chunks))

            preview_select.on_value_change(lambda _: update_preview())
            update_preview()
            ui.button("Download selected AI interview JSON", on_click=lambda: ui.download(AI_RESPONSES_DIR / preview_select.value), color="accent").classes("q-mt-md")


def render_analysis_studio() -> None:
    ai_files = get_ai_response_files()
    real_ready = REAL_TRANSCRIPT_PATH.exists()

    with ui.card().classes("section-card w-full q-pa-lg"):
        ui.label("Analysis Studio").classes("section-title")
        ui.label(
            "Run structured comparisons, Gioia outputs, and exports from the same workspace. The emphasis here is on usable interpretation, not just generation."
        ).classes("section-note")

        if not real_ready or not ai_files:
            ui.label(
                "Load a real transcript and generate at least one AI interview before running analysis."
            ).classes("research-note q-mt-md")
            return

        selected_ai = ui.select(
            options={path.name: path.stem.replace("_", " ").title() for path in ai_files},
            value=ai_files[0].name,
            label="Choose AI interview for analysis",
        ).classes("w-full q-mt-md")

        narrative_box = ui.markdown().classes("w-full q-mt-lg")
        comparison_table_wrap = ui.column().classes("w-full q-mt-md")

        def selected_ai_path() -> Path:
            return AI_RESPONSES_DIR / selected_ai.value

        def render_structured(payload: dict[str, Any]) -> None:
            comparison_table_wrap.clear()
            with comparison_table_wrap:
                overview = payload.get("overview", {})
                if overview.get("key_takeaway"):
                    ui.label(overview["key_takeaway"]).classes("research-note")

                rows = payload.get("comparison_table", [])
                if rows:
                    ui.table(
                        columns=[
                            {"name": "theme", "label": "Theme", "field": "theme"},
                            {"name": "real_pattern", "label": "Real Pattern", "field": "real_pattern"},
                            {"name": "ai_pattern", "label": "AI Pattern", "field": "ai_pattern"},
                            {"name": "difference", "label": "Difference", "field": "difference"},
                            {"name": "research_implication", "label": "Research Implication", "field": "research_implication"},
                        ],
                        rows=rows,
                        pagination=8,
                    ).classes("w-full")

                quote_row = ui.row().classes("w-full q-col-gutter-lg q-mt-md items-start")
                with quote_row:
                    with ui.card().classes("table-card col q-pa-md"):
                        ui.label("Real Interview Quotes").classes("section-title")
                        for item in payload.get("quotes", {}).get("real", []):
                            ui.markdown(f"**{item.get('theme', '')}**  \n{item.get('quote', '')}  \n_{item.get('why_it_matters', '')}_")
                    with ui.card().classes("table-card col q-pa-md"):
                        ui.label("AI Interview Quotes").classes("section-title")
                        for item in payload.get("quotes", {}).get("ai", []):
                            ui.markdown(f"**{item.get('theme', '')}**  \n{item.get('quote', '')}  \n_{item.get('why_it_matters', '')}_")

                theme_items = payload.get("theme_review", [])
                if theme_items:
                    with ui.card().classes("analysis-card w-full q-pa-md q-mt-md"):
                        ui.label("Theme Review").classes("section-title")
                        for item in theme_items:
                            with ui.expansion(f"{item.get('dimension', 'Dimension')} • {item.get('theme', 'Theme')}", value=False).classes("w-full"):
                                ui.markdown(f"**First-order concepts**  \n{', '.join(item.get('first_order_concepts', []))}")
                                ui.markdown(f"**Real evidence**  \n{item.get('real_evidence', '')}")
                                ui.markdown(f"**AI evidence**  \n{item.get('ai_evidence', '')}")
                                ui.markdown(f"**Model note**  \n{item.get('review_note', '')}")

            narrative_box.set_content(payload.get("markdown_report", ""))

        def run_selected_comparison() -> None:
            try:
                ai_path = selected_ai_path()
                base_name = f"comparison_analysis_{ai_path.stem}"
                payload = run_structured_comparison(ai_path)
                if payload:
                    save_structured_comparison(base_name, payload)
                    state["latest_comparison_structured"] = payload
                    state["latest_comparison"] = payload.get("markdown_report", "")
                    render_structured(payload)
                    ui.notify("Structured comparison analysis generated.", type="positive")
                    return
                markdown = run_comparison(ai_path)
                save_markdown(OUTPUTS_DIR / f"{base_name}.md", f"Real vs AI Interview Comparison ({ai_path.name})", markdown)
                state["latest_comparison"] = markdown
                narrative_box.set_content(markdown)
                comparison_table_wrap.clear()
                ui.notify("Saved markdown comparison because JSON parsing failed.", type="warning")
            except Exception as exc:
                notify_error("Comparison analysis failed.", exc)

        def analyze_real() -> None:
            try:
                analysis = run_real_interview_analysis()
                save_markdown(OUTPUTS_DIR / "real_interview_analysis.md", "Real Interview Gioia Analysis", analysis)
                state["latest_real_analysis"] = analysis
                narrative_box.set_content(analysis)
                comparison_table_wrap.clear()
                ui.notify("Real interview analysis generated.", type="positive")
            except Exception as exc:
                notify_error("Real interview analysis failed.", exc)

        def analyze_ai() -> None:
            try:
                ai_path = selected_ai_path()
                output_path = OUTPUTS_DIR / f"{ai_path.stem}_gioia.md"
                analysis = analyze_gioia(str(ai_path), str(output_path), settings=state["study_settings"])
                state["latest_ai_analysis"] = analysis
                narrative_box.set_content(analysis)
                comparison_table_wrap.clear()
                ui.notify("AI interview analysis generated.", type="positive")
            except Exception as exc:
                notify_error("AI interview analysis failed.", exc)

        def export_selected_ai() -> None:
            try:
                ai_path = selected_ai_path()
                export_all_formats(str(ai_path), ai_path.stem, output_dir=str(EXPORTS_DIR))
                ui.notify("Interview exported to DOCX, PDF, CSV, TXT, and HTML.", type="positive")
                refresh_page()
            except Exception as exc:
                notify_error("Export failed.", exc)

        with ui.row().classes("q-gutter-md q-mt-md"):
            ui.button("Run comparison analysis", on_click=run_selected_comparison, color="primary")
            ui.button("Analyze real interview", on_click=analyze_real, color="secondary")
            ui.button("Analyze selected AI interview", on_click=analyze_ai, color="accent")
            ui.button("Export selected AI interview", on_click=export_selected_ai, color="positive")

        if state.get("latest_comparison_structured"):
            render_structured(state["latest_comparison_structured"])
        elif state.get("latest_comparison"):
            narrative_box.set_content(state["latest_comparison"])

        saved_output_files = sorted(
            [path for path in OUTPUTS_DIR.iterdir() if path.is_file() and path.suffix in {".md", ".json", ".csv", ".html"}]
        )
        exported_files = sorted([path for path in EXPORTS_DIR.iterdir() if path.is_file()])

        with ui.row().classes("w-full q-col-gutter-lg q-mt-lg items-start"):
            with ui.card().classes("table-card col q-pa-md"):
                ui.label("Saved Analyses").classes("section-title")
                for path in saved_output_files:
                    ui.button(path.name, on_click=lambda p=path: ui.download(p), flat=True).classes("justify-start w-full")
            with ui.card().classes("table-card col q-pa-md"):
                ui.label("Exported Transcripts").classes("section-title")
                for path in exported_files:
                    ui.button(path.name, on_click=lambda p=path: ui.download(p), flat=True).classes("justify-start w-full")


build_ui()
ui.run(title="Qualitative AI Interview Studio", host="127.0.0.1", reload=False)
