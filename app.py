import json
import os
import csv
import re
from pathlib import Path

import streamlit as st

from config import get_secret

try:
    import openai
    from scripts.analyze_gioia import analyze_gioia
    from scripts.export_results import export_all_formats, export_both
    from scripts.simulate_interviews import simulate_interview
    from utils.pdf_parser import (
        extract_questions_with_ai,
        extract_text_from_pdf,
        validate_and_improve_questions,
    )
    from utils.persona_parser import (
        extract_persona_info_with_ai,
        extract_text_from_docx,
        extract_text_from_pdf_persona,
        validate_persona_data,
    )
except ModuleNotFoundError as exc:
    missing_module = exc.name or "a required package"
    st.set_page_config(page_title="Qualitative AI Interview Studio", page_icon="Q", layout="wide")
    st.error(f"Missing dependency: `{missing_module}`")
    st.markdown(
        """
        This app is being launched with a Python environment that does not have the project dependencies installed.

        Use one of these commands from the project folder:

        ```bash
        ./run.sh
        ```

        or

        ```bash
        source venv/bin/activate
        streamlit run app.py
        ```

        If the environment has not been set up yet, run:

        ```bash
        python install.py
        ```
        """
    )
    st.stop()


st.set_page_config(
    page_title="Qualitative AI Interview Studio",
    page_icon="Q",
    layout="wide",
    initial_sidebar_state="expanded",
)


APP_DIRS = ["personas", "data", "data/ai_responses", "outputs", "questions", "exports", "study_protocols"]
QUESTIONS_PATH = Path("questions/questions.txt")
REAL_TRANSCRIPT_PATH = Path("data/real_interview_transcript.txt")
PERSONAS_DIR = Path("personas")
AI_RESPONSES_DIR = Path("data/ai_responses")
OUTPUTS_DIR = Path("outputs")
EXPORTS_DIR = Path("exports")
STUDY_PROTOCOLS_DIR = Path("study_protocols")


for dir_path in APP_DIRS:
    os.makedirs(dir_path, exist_ok=True)


def default_study_settings() -> dict:
    return {
        "protocol_name": "default-study-protocol",
        "model": "gpt-3.5-turbo",
        "temperature": 0.55,
        "analysis_temperature": 0.3,
        "max_answer_tokens": 500,
        "analysis_max_tokens": 2200,
        "quote_count": 4,
        "coding_depth": "Standard",
        "shared_context": "",
        "interview_style": (
            "Answer like a real participant in an interview. "
            "Use concrete language, acknowledge uncertainty when appropriate, and avoid sounding like a summary report."
        ),
        "consistency_rules": (
            "Stay consistent with the persona across all questions. "
            "Do not become more polished, confident, or generic as the interview continues."
        ),
        "analysis_focus": (
            "Pay attention to differences in specificity, emotional texture, lived context, and whether the AI sounds too tidy or generalized."
        ),
    }


def init_session_state() -> None:
    defaults = {
        "questions": None,
        "uploaded_files": {"context": None, "questions": None},
        "personas": [],
        "manual_persona_text": "",
        "manual_persona_data": None,
        "latest_comparison": None,
        "latest_comparison_structured": None,
        "latest_comparison_key": None,
        "latest_real_analysis": None,
        "latest_ai_analysis": None,
        "last_previewed_ai_file": None,
        "study_settings": default_study_settings(),
        "theme_review_notes": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Instrument+Serif:ital@0;1&display=swap');

        :root {
            --bg: #f5efe4;
            --surface: rgba(255, 251, 244, 0.82);
            --surface-strong: #fffaf2;
            --ink: #1f1c18;
            --muted: #5c554b;
            --line: rgba(80, 64, 38, 0.14);
            --accent: #0d6b63;
            --accent-2: #d96b3b;
            --accent-soft: rgba(13, 107, 99, 0.09);
            --shadow: 0 14px 40px rgba(53, 40, 22, 0.08);
            --radius: 22px;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(217, 107, 59, 0.16), transparent 28%),
                radial-gradient(circle at top right, rgba(13, 107, 99, 0.18), transparent 30%),
                linear-gradient(180deg, #f8f3ea 0%, #f2eadf 100%);
            color: var(--ink);
        }

        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2rem;
            max-width: 1440px;
        }

        h1, h2, h3, h4 {
            font-family: "Space Grotesk", sans-serif !important;
            color: var(--ink);
            letter-spacing: -0.02em;
        }

        p, li, label, .stMarkdown, .stText, .stCaption {
            font-family: "Space Grotesk", sans-serif !important;
            color: var(--ink) !important;
        }

        label, .stTextInput label, .stTextArea label, .stSelectbox label, .stRadio label, .stNumberInput label {
            color: var(--ink) !important;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(255, 248, 239, 0.97), rgba(247, 238, 225, 0.98));
            border-right: 1px solid var(--line);
        }

        [data-testid="stSidebar"] * {
            color: var(--ink) !important;
        }

        [data-testid="stMarkdownContainer"] * {
            color: var(--ink);
        }

        [data-testid="stMetric"] {
            background: rgba(255, 250, 242, 0.96);
            border: 1px solid rgba(80, 64, 38, 0.12);
            border-radius: 18px;
            padding: 0.45rem 0.7rem;
            box-shadow: var(--shadow);
            min-height: 96px;
        }

        [data-testid="stMetric"] * {
            color: var(--ink) !important;
        }

        [data-testid="stMetricLabel"] {
            color: var(--muted) !important;
        }

        [data-testid="stMetricLabel"] p {
            color: var(--muted) !important;
            font-size: 0.78rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        [data-testid="stMetricValue"] {
            color: #1f1c18 !important;
        }

        [data-testid="stMetricValue"] > div,
        [data-testid="stMetricValue"] p {
            color: #1f1c18 !important;
            font-size: 1.45rem !important;
            font-weight: 700 !important;
            line-height: 1.1 !important;
        }

        div[data-baseweb="tab-list"] {
            gap: 0.4rem;
            background: rgba(255, 250, 242, 0.72);
            padding: 0.35rem;
            border-radius: 18px;
            border: 1px solid var(--line);
        }

        button[data-baseweb="tab"] {
            background: transparent !important;
            color: var(--muted) !important;
            border-radius: 14px !important;
            border: 1px solid transparent !important;
            font-weight: 700 !important;
            min-height: 44px !important;
            padding: 0.55rem 1rem !important;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            background: rgba(13, 107, 99, 0.14) !important;
            color: var(--ink) !important;
            border-color: rgba(13, 107, 99, 0.28) !important;
            box-shadow: 0 8px 20px rgba(13, 107, 99, 0.12);
        }

        button[data-baseweb="tab"]:hover {
            background: rgba(13, 107, 99, 0.10) !important;
            color: var(--ink) !important;
        }

        button[kind="primary"] {
            background: linear-gradient(135deg, #d7eee9, #c6e5df) !important;
            border: 1px solid rgba(13, 107, 99, 0.22) !important;
            color: var(--ink) !important;
        }

        button[kind="secondary"] {
            border-radius: 999px !important;
            border: 1px solid rgba(13, 107, 99, 0.22) !important;
            color: var(--ink) !important;
            background: rgba(255, 250, 242, 0.88) !important;
        }

        [data-testid="stFileUploader"] {
            background: rgba(255, 250, 242, 0.88);
            border-radius: 18px;
            padding: 0.25rem;
        }

        [data-testid="stFileUploader"] section {
            background: #fffaf2 !important;
            border: 1.5px dashed rgba(13, 107, 99, 0.35) !important;
            border-radius: 18px !important;
            padding: 1rem !important;
        }

        [data-testid="stFileUploader"] * {
            color: var(--ink) !important;
        }

        [data-testid="stFileUploader"] small,
        [data-testid="stFileUploader"] span,
        [data-testid="stFileUploader"] p {
            color: var(--muted) !important;
        }

        [data-testid="stFileUploader"] button {
            background: linear-gradient(135deg, #d7eee9, #c6e5df) !important;
            color: var(--ink) !important;
            border: 1px solid rgba(13, 107, 99, 0.22) !important;
            font-weight: 700 !important;
        }

        [data-testid="stFileUploader"] button:hover {
            background: linear-gradient(135deg, #cde8e2, #bddfd8) !important;
            color: var(--ink) !important;
        }

        div[role="radiogroup"] label,
        div[role="radiogroup"] p,
        div[role="radiogroup"] span {
            color: var(--ink) !important;
        }

        div[role="radiogroup"] > label {
            background: rgba(255, 250, 242, 0.85);
            border-radius: 999px;
            padding: 0.2rem 0.35rem;
        }

        .stTextArea textarea,
        .stTextInput input,
        .stNumberInput input,
        .stSelectbox input {
            background: #fffaf2 !important;
            color: var(--ink) !important;
            border: 1px solid rgba(80, 64, 38, 0.16) !important;
        }

        .stTextArea textarea::placeholder,
        .stTextInput input::placeholder,
        .stNumberInput input::placeholder {
            color: #6b645a !important;
            opacity: 1 !important;
        }

        [data-baseweb="base-input"],
        [data-baseweb="select"] > div,
        [data-baseweb="textarea"] {
            background: #fffaf2 !important;
            color: var(--ink) !important;
        }

        [data-baseweb="select"] *, 
        [data-baseweb="base-input"] *,
        [data-baseweb="textarea"] * {
            color: var(--ink) !important;
        }

        [data-testid="stAlert"] {
            border-radius: 18px;
            border: 1px solid rgba(80, 64, 38, 0.12);
        }

        [data-testid="stAlert"] * {
            color: var(--ink) !important;
        }

        [data-testid="stAlert"][kind="warning"] {
            background: #fff6cf !important;
        }

        [data-testid="stAlert"][kind="info"] {
            background: #eaf3f1 !important;
        }

        [data-testid="stAlert"][kind="success"] {
            background: #e8f5ee !important;
        }

        [data-testid="stAlert"][kind="error"] {
            background: #f9e8e4 !important;
        }

        .hero {
            background:
                linear-gradient(135deg, rgba(255, 250, 242, 0.92), rgba(246, 235, 220, 0.92)),
                radial-gradient(circle at right top, rgba(13, 107, 99, 0.10), transparent 32%);
            border: 1px solid var(--line);
            border-radius: 30px;
            padding: 1.4rem 1.5rem 1.5rem 1.5rem;
            box-shadow: var(--shadow);
            margin-bottom: 1rem;
        }

        .hero-kicker {
            text-transform: uppercase;
            font-size: 0.74rem;
            letter-spacing: 0.18em;
            color: var(--accent);
            font-weight: 700;
            margin-bottom: 0.45rem;
        }

        .hero-title {
            font-family: "Instrument Serif", serif !important;
            font-size: 3rem;
            line-height: 0.95;
            margin-bottom: 0.8rem;
        }

        .hero-copy {
            max-width: 880px;
            color: var(--muted);
            font-size: 1rem;
            line-height: 1.6;
        }

        .panel {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: var(--radius);
            padding: 1.05rem 1.1rem;
            box-shadow: var(--shadow);
            margin-bottom: 0.9rem;
        }

        .panel-title {
            font-family: "Space Grotesk", sans-serif;
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--accent);
            margin-bottom: 0.45rem;
            font-weight: 700;
        }

        .panel strong {
            color: var(--ink);
        }

        .subtle {
            color: var(--muted);
        }

        .mini-card-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 0.8rem;
            margin: 0.75rem 0 0.35rem 0;
        }

        .mini-card {
            background: var(--surface-strong);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 0.9rem 1rem;
        }

        .mini-card-label {
            font-size: 0.74rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--muted);
            margin-bottom: 0.25rem;
            font-weight: 700;
        }

        .mini-card-value {
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--ink);
        }

        .research-note {
            border-left: 4px solid var(--accent-2);
            background: rgba(217, 107, 59, 0.08);
            border-radius: 14px;
            padding: 0.9rem 1rem;
            margin: 0.75rem 0;
            color: #4d382a;
        }

        .status-pill {
            display: inline-block;
            padding: 0.28rem 0.7rem;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 700;
            margin-right: 0.35rem;
            margin-bottom: 0.35rem;
            background: var(--accent-soft);
            color: var(--accent);
        }

        .persona-card {
            background: var(--surface-strong);
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 0.95rem 1rem;
            min-height: 190px;
        }

        .persona-name {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }

        .persona-meta {
            color: var(--muted);
            margin-bottom: 0.55rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
    st.session_state.questions = questions


def save_transcript(text: str) -> None:
    REAL_TRANSCRIPT_PATH.write_text(text, encoding="utf-8")


def get_persona_files() -> list[Path]:
    return sorted(PERSONAS_DIR.glob("*.json"))


def load_persona(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_persona(persona_data: dict) -> Path:
    validated = validate_persona_data(persona_data)
    slug = validated["name"].strip().lower().replace(" ", "_")
    filename = PERSONAS_DIR / f"{slug}.json"
    filename.write_text(json.dumps(validated, indent=2), encoding="utf-8")
    return filename


def get_ai_response_files() -> list[Path]:
    return sorted(AI_RESPONSES_DIR.glob("*.json"))


def load_ai_interview(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_protocol_files() -> list[Path]:
    return sorted(STUDY_PROTOCOLS_DIR.glob("*.json"))


def load_protocol(path: Path) -> dict:
    settings = default_study_settings()
    settings.update(json.loads(path.read_text(encoding="utf-8")))
    return settings


def save_protocol(settings: dict) -> Path:
    slug = settings.get("protocol_name", "study-protocol").strip().lower().replace(" ", "_")
    path = STUDY_PROTOCOLS_DIR / f"{slug}.json"
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return path


def extract_json_payload(raw_text: str) -> dict | None:
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


def save_structured_comparison(base_name: str, payload: dict) -> dict[str, Path]:
    json_path = OUTPUTS_DIR / f"{base_name}.json"
    md_path = OUTPUTS_DIR / f"{base_name}.md"
    csv_path = OUTPUTS_DIR / f"{base_name}.csv"
    html_path = OUTPUTS_DIR / f"{base_name}.html"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    markdown_report = payload.get("markdown_report", "")
    md_path.write_text(markdown_report, encoding="utf-8")

    rows = payload.get("comparison_table", [])
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["theme", "real_pattern", "ai_pattern", "difference", "research_implication"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "theme": row.get("theme", ""),
                    "real_pattern": row.get("real_pattern", ""),
                    "ai_pattern": row.get("ai_pattern", ""),
                    "difference": row.get("difference", ""),
                    "research_implication": row.get("research_implication", ""),
                }
            )

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


def render_panel(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="panel">
            <div class="panel-title">{title}</div>
            <div>{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_research_note(text: str) -> None:
    st.markdown(f'<div class="research-note">{text}</div>', unsafe_allow_html=True)


def render_persona_summary(persona_path: Path) -> None:
    persona = load_persona(persona_path)
    age = persona.get("age") if persona.get("age") is not None else "Age not specified"
    opinions = persona.get("opinions", {})
    st.markdown(
        f"""
        <div class="persona-card">
            <div class="persona-name">{persona.get("name", persona_path.stem)}</div>
            <div class="persona-meta">{persona.get("job", "Role not specified")} | {age}</div>
            <div><strong>Education:</strong> {persona.get("education", "Not specified")}</div>
            <div style="margin-top:0.35rem;"><strong>Personality:</strong> {persona.get("personality", "Not specified")}</div>
            <div style="margin-top:0.45rem;" class="subtle"><strong>AI stance:</strong> {opinions.get("AI", "Not specified")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="hero-kicker">Qualitative Research Workflow</div>
            <div class="hero-title">Build AI interview studies people actually want to use.</div>
            <div class="hero-copy">
                This studio is designed around a common qualitative workflow:
                define the research context, use a shared interview guide, simulate persona-based interviews,
                and compare AI output against real transcripts with Gioia-ready structure. The interface favors
                clarity for active analysis while still feeling polished enough to invite repeated use.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_overview_metrics() -> None:
    questions = st.session_state.questions or load_questions()
    personas = get_persona_files()
    ai_interviews = get_ai_response_files()
    transcript_exists = REAL_TRANSCRIPT_PATH.exists()

    a, b, c, d = st.columns(4)
    a.metric("Research Guide", f"{len(questions)} questions" if questions else "Not loaded")
    b.metric("Personas", len(personas))
    c.metric("AI Interviews", len(ai_interviews))
    d.metric("Real Transcript", "Ready" if transcript_exists else "Missing")


def render_sidebar() -> None:
    st.sidebar.markdown("## Study Progress")
    questions = st.session_state.questions or load_questions()
    personas = get_persona_files()
    ai_interviews = get_ai_response_files()
    transcript_ready = REAL_TRANSCRIPT_PATH.exists()

    steps = [
        ("Real transcript loaded", transcript_ready),
        ("Interview guide loaded", bool(questions)),
        ("Personas prepared", bool(personas)),
        ("Simulations generated", bool(ai_interviews)),
    ]
    for label, ready in steps:
        state = "Ready" if ready else "Waiting"
        st.sidebar.markdown(f"- {label}: **{state}**")

    st.sidebar.markdown("---")
    st.sidebar.markdown("## Research Fit")
    st.sidebar.caption(
        "Designed for researchers comparing real interviews with persona-based AI interview simulations."
    )
    st.sidebar.markdown(
        "- Match AI interviews to the same guide used with human participants.\n"
        "- Preserve persona context so responses feel anchored, not generic.\n"
        "- Compare whole-interview patterns, not just isolated answers.\n"
        "- Surface where AI becomes too clean, too uniform, or too textbook."
    )
    st.sidebar.markdown("---")
    api_key = get_secret("OPENAI_API_KEY")
    if api_key:
        st.sidebar.success("API key detected")
    else:
        st.sidebar.error("No OpenAI API key configured")
        st.sidebar.caption("Set `OPENAI_API_KEY` in Streamlit secrets, `.env`, or your shell.")


def render_protocol_editor() -> None:
    st.markdown("### Study Protocol")
    st.caption("Set reusable instructions so simulations and analyses stay consistent across a study.")

    settings = dict(st.session_state.study_settings)

    settings["shared_context"] = st.text_area(
        "Shared study context",
        value=settings.get("shared_context", ""),
        height=120,
        help="Background that should inform all simulations and analyses in this study.",
    )
    settings["interview_style"] = st.text_area(
        "Interview style guidance",
        value=settings.get("interview_style", ""),
        height=100,
        help="Instructions that keep the AI interview voice natural and researcher-appropriate.",
    )
    settings["consistency_rules"] = st.text_area(
        "Consistency rules",
        value=settings.get("consistency_rules", ""),
        height=100,
        help="Rules that reduce drift, generic phrasing, or inconsistent personas across questions.",
    )
    settings["analysis_focus"] = st.text_area(
        "Analysis focus",
        value=settings.get("analysis_focus", ""),
        height=100,
        help="Guidance that should shape comparisons, quote selection, and thematic interpretation.",
    )

    action_cols = st.columns(3)
    with action_cols[0]:
        if st.button("Apply protocol settings", use_container_width=True):
            st.session_state.study_settings = settings
            st.success("Protocol settings applied.")
    with action_cols[1]:
        if st.button("Save protocol", use_container_width=True):
            st.session_state.study_settings = settings
            if not settings.get("protocol_name"):
                settings["protocol_name"] = "saved-study-protocol"
            path = save_protocol(settings)
            st.success(f"Saved protocol to {path.name}.")
    with action_cols[2]:
        if st.button("Reset protocol", use_container_width=True):
            st.session_state.study_settings = default_study_settings()
            st.success("Protocol reset to defaults.")
            st.rerun()


def process_transcript_upload(uploaded_file) -> None:
    try:
        if uploaded_file.type == "application/pdf":
            transcript_text = extract_text_from_pdf(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            transcript_text = extract_text_from_docx(uploaded_file)
        else:
            transcript_text = uploaded_file.read().decode("utf-8")

        if not transcript_text:
            st.error("Could not extract text from the transcript file.")
            return

        save_transcript(transcript_text)
        st.session_state.uploaded_files["context"] = uploaded_file.name
        st.success(f"Transcript captured with {len(transcript_text):,} characters.")
        st.text_area("Transcript preview", transcript_text[:3500], height=260)
        st.download_button(
            "Download extracted transcript",
            data=transcript_text,
            file_name=f"{Path(uploaded_file.name).stem}.txt",
            mime="text/plain",
            key="download_transcript",
        )
    except Exception as exc:
        st.error(f"Error processing transcript: {exc}")


def process_question_upload(uploaded_file) -> None:
    try:
        questions: list[str] = []
        if uploaded_file.type == "application/pdf":
            pdf_text = extract_text_from_pdf(uploaded_file)
            if not pdf_text:
                st.error("Could not extract text from the PDF.")
                return
            st.text_area("Question guide preview", pdf_text[:3000], height=220)
            questions = extract_questions_with_ai(pdf_text)
        else:
            questions = [line.decode("utf-8").strip() for line in uploaded_file.readlines() if line.strip()]

        if not questions:
            st.error("No questions were extracted from the uploaded file.")
            return

        save_questions(questions)
        st.session_state.uploaded_files["questions"] = uploaded_file.name
        st.success(f"{len(questions)} interview questions loaded.")
    except Exception as exc:
        st.error(f"Error processing questions: {exc}")


def simulate_selected_personas(selected_personas: list[Path]) -> None:
    if not selected_personas:
        st.warning("Choose at least one persona to simulate.")
        return

    settings = st.session_state.study_settings
    for persona_path in selected_personas:
        output_path = AI_RESPONSES_DIR / f"{persona_path.stem}_responses.json"
        with st.spinner(f"Simulating {persona_path.stem.replace('_', ' ').title()}..."):
            simulate_interview(str(persona_path), str(QUESTIONS_PATH), str(output_path), settings=settings)
        st.success(f"Interview ready for {persona_path.stem.replace('_', ' ').title()}.")


def run_comparison(ai_file: Path) -> str:
    real_transcript = safe_read_text(REAL_TRANSCRIPT_PATH)
    ai_responses = load_ai_interview(ai_file)
    client = openai.OpenAI(api_key=get_secret("OPENAI_API_KEY"))
    settings = st.session_state.study_settings

    ai_text = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in ai_responses])

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

    response = client.chat.completions.create(
        model=settings.get("model", "gpt-3.5-turbo"),
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
    return response.choices[0].message.content


def run_structured_comparison(ai_file: Path) -> dict | None:
    real_transcript = safe_read_text(REAL_TRANSCRIPT_PATH)
    ai_responses = load_ai_interview(ai_file)
    ai_text = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in ai_responses])
    settings = st.session_state.study_settings
    client = openai.OpenAI(api_key=get_secret("OPENAI_API_KEY"))

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

    response = client.chat.completions.create(
        model=settings.get("model", "gpt-3.5-turbo"),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert qualitative researcher. "
                    "Return valid JSON only. Do not wrap it in markdown fences."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=settings.get("analysis_max_tokens", 2200),
        temperature=settings.get("analysis_temperature", 0.3),
    )
    return extract_json_payload(response.choices[0].message.content)


def run_real_interview_analysis() -> str:
    real_transcript = safe_read_text(REAL_TRANSCRIPT_PATH)
    client = openai.OpenAI(api_key=get_secret("OPENAI_API_KEY"))
    settings = st.session_state.study_settings

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

    response = client.chat.completions.create(
        model=settings.get("model", "gpt-3.5-turbo"),
        messages=[
            {"role": "system", "content": "You are an expert qualitative researcher using the Gioia methodology."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=settings.get("analysis_max_tokens", 2200),
        temperature=settings.get("analysis_temperature", 0.3),
    )
    return response.choices[0].message.content


def save_markdown(path: Path, title: str, body: str) -> None:
    path.write_text(f"# {title}\n\n{body}", encoding="utf-8")


init_session_state()
inject_css()

merged_settings = default_study_settings()
merged_settings.update(st.session_state.study_settings)
st.session_state.study_settings = merged_settings

if not st.session_state.questions:
    st.session_state.questions = load_questions() or None

render_sidebar()
render_header()
render_overview_metrics()

render_research_note(
    "A recurring product need in this workflow is that researchers want AI interviews that are easy to set up, "
    "but also easy to interrogate. The interface below is organized around that sequence and keeps comparison quality front and center."
)

tab1, tab2, tab3, tab4 = st.tabs(
    ["Study Design", "Persona Studio", "Simulation Lab", "Analysis Studio"]
)


with tab1:
    left, right = st.columns([1.4, 1], gap="large")

    with left:
        render_panel(
            "Study Design",
            (
                "Load the real transcript and the shared interview guide first. "
                "The quality of the comparison depends heavily on using the same guide across real and simulated interviews."
            ),
        )

        transcript_file = st.file_uploader(
            "Upload real interview transcript",
            type=["docx", "pdf", "txt"],
            help="Use the human interview transcript you want AI responses compared against.",
        )
        if transcript_file:
            process_transcript_upload(transcript_file)
        elif REAL_TRANSCRIPT_PATH.exists():
            transcript_text = safe_read_text(REAL_TRANSCRIPT_PATH)
            st.success("A real transcript is already saved in the workspace.")
            st.text_area("Saved transcript preview", transcript_text[:3500], height=250)

        st.divider()

        question_file = st.file_uploader(
            "Upload interview guide",
            type=["txt", "pdf"],
            help="TXT should contain one question per line. PDFs will be parsed and questions inferred.",
        )
        if question_file:
            process_question_upload(question_file)

        current_questions = st.session_state.questions or load_questions()
        if current_questions:
            with st.expander("Review and refine the interview guide", expanded=True):
                edited_questions = st.text_area(
                    "Interview questions",
                    value="\n".join(current_questions),
                    height=320,
                )
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("Save question guide", use_container_width=True):
                        revised = [line.strip() for line in edited_questions.splitlines() if line.strip()]
                        save_questions(revised)
                        st.success(f"Saved {len(revised)} questions.")
                with col_b:
                    if st.button("Polish questions with AI", use_container_width=True):
                        revised = [line.strip() for line in edited_questions.splitlines() if line.strip()]
                        improved = validate_and_improve_questions(revised)
                        if improved:
                            save_questions(improved)
                            st.success("Question guide improved and saved.")
                            st.rerun()

    with right:
        render_panel(
            "Research Foundation",
            (
                "The redesign is grounded in common qualitative interview workflows: "
                "shared interview guides, persona-based simulations, transcript comparison, and structured thematic analysis."
            ),
        )
        st.markdown(
            """
            <div class="mini-card-grid">
                <div class="mini-card">
                    <div class="mini-card-label">Workflow</div>
                    <div class="mini-card-value">Guide -> Persona -> AI Interview -> Comparison</div>
                </div>
                <div class="mini-card">
                    <div class="mini-card-label">Core Need</div>
                    <div class="mini-card-value">Useful AI output without losing qualitative nuance</div>
                </div>
                <div class="mini-card">
                    <div class="mini-card-label">Observed Risk</div>
                    <div class="mini-card-value">AI becomes too tidy, generic, and repetitive</div>
                </div>
                <div class="mini-card">
                    <div class="mini-card-label">Design Response</div>
                    <div class="mini-card-value">Stronger previews, batch tools, and comparison-first navigation</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_research_note(
            "A recurring challenge in this workflow is that AI answers are easier to follow but often less personal, less situational, "
            "and too similar across personas. This UI leans into that by making persona review and transcript comparison much more prominent."
        )
        st.markdown("##### Saved Assets")
        st.markdown(
            f'<span class="status-pill">Transcript {"ready" if REAL_TRANSCRIPT_PATH.exists() else "missing"}</span>'
            f'<span class="status-pill">{len(current_questions)} questions</span>'
            f'<span class="status-pill">{len(get_persona_files())} personas</span>'
            f'<span class="status-pill">{len(get_protocol_files())} saved protocols</span>',
            unsafe_allow_html=True,
        )
        st.divider()
        render_protocol_editor()


with tab2:
    persona_files = get_persona_files()
    st.markdown("### Persona Studio")
    st.caption(
        "Build respondents that feel grounded enough for comparative qualitative work, not just demo personas."
    )

    if persona_files:
        persona_cols = st.columns(min(3, max(1, len(persona_files))))
        for idx, persona_path in enumerate(persona_files):
            with persona_cols[idx % len(persona_cols)]:
                render_persona_summary(persona_path)
    else:
        st.info("No personas saved yet. Add one below.")

    render_research_note(
        "Persona-conditioned interviewing works best when the source material is specific. Generic personas tend to produce generic answers, "
        "so this area now puts much more weight on reviewing role, education, personality, and original source text."
    )

    creation_method = st.radio(
        "Persona creation mode",
        ["Manual narrative", "Upload source document"],
        horizontal=True,
    )

    if creation_method == "Manual narrative":
        st.text_area(
            "Persona narrative",
            key="manual_persona_text",
            height=220,
            placeholder=(
                "Describe the participant in enough detail that the AI can answer in a grounded way. "
                "Include role, lived context, values, experience, tensions, and how they think about the focal topic."
            ),
        )
        action_cols = st.columns([1, 1.2, 1.2])
        with action_cols[0]:
            if st.button("Extract persona", use_container_width=True):
                if st.session_state.manual_persona_text.strip():
                    with st.spinner("Structuring persona from the narrative..."):
                        persona_counter = len(persona_files) + 1
                        st.session_state.manual_persona_data = extract_persona_info_with_ai(
                            st.session_state.manual_persona_text, persona_counter
                        )
                else:
                    st.warning("Add a persona narrative first.")
        with action_cols[1]:
            if st.button("Clear draft", use_container_width=True):
                st.session_state.manual_persona_text = ""
                st.session_state.manual_persona_data = None
                st.rerun()

        if st.session_state.manual_persona_data:
            persona_data = st.session_state.manual_persona_data
            st.markdown("#### Review extracted persona")
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Name", value=persona_data["name"], key="manual_name")
                age_input = st.number_input(
                    "Age (0 = unspecified)",
                    min_value=0,
                    max_value=99,
                    value=persona_data.get("age") or 0,
                    key="manual_age",
                )
                job = st.text_input("Role / profession", value=persona_data["job"], key="manual_job")
                education = st.text_input("Education", value=persona_data["education"], key="manual_education")
            with col2:
                personality = st.text_area(
                    "Personality and disposition",
                    value=persona_data["personality"],
                    height=140,
                    key="manual_personality",
                )
                ai_opinion = st.text_input(
                    "Opinion on AI / technology",
                    value=persona_data.get("opinions", {}).get("AI", "Not specified"),
                    key="manual_ai_opinion",
                )
                remote_work_opinion = st.text_input(
                    "Opinion on remote work",
                    value=persona_data.get("opinions", {}).get("Remote Work", "Not specified"),
                    key="manual_remote_opinion",
                )

            if st.button("Save persona", use_container_width=True):
                saved = save_persona(
                    {
                        "name": name,
                        "age": None if age_input == 0 else age_input,
                        "job": job,
                        "education": education,
                        "personality": personality,
                        "original_text": persona_data.get("original_text", st.session_state.manual_persona_text),
                        "opinions": {"AI": ai_opinion, "Remote Work": remote_work_opinion},
                    }
                )
                st.success(f"Saved persona to {saved.name}.")
                st.session_state.manual_persona_data = None
                st.session_state.manual_persona_text = ""
                st.rerun()

    else:
        uploaded_persona = st.file_uploader("Upload persona source", type=["docx", "pdf"], key="persona_upload")
        if uploaded_persona:
            try:
                if uploaded_persona.type == "application/pdf":
                    document_text = extract_text_from_pdf_persona(uploaded_persona)
                else:
                    document_text = extract_text_from_docx(uploaded_persona)

                if not document_text:
                    st.error("Could not extract text from the persona document.")
                else:
                    st.text_area("Source preview", document_text[:3500], height=220)
                    if st.button("Extract persona from document", use_container_width=True):
                        with st.spinner("Analyzing persona source..."):
                            persona_counter = len(persona_files) + 1
                            st.session_state.manual_persona_data = extract_persona_info_with_ai(
                                document_text, persona_counter
                            )
                            st.session_state.manual_persona_text = document_text
                            st.rerun()
            except Exception as exc:
                st.error(f"Error processing persona document: {exc}")


with tab3:
    st.markdown("### Simulation Lab")
    st.caption(
        "Run persona-based interviews in batches and inspect the generated transcripts before moving into analysis."
    )

    questions = st.session_state.questions or load_questions()
    persona_files = get_persona_files()
    ai_files = get_ai_response_files()

    readiness_col, action_col = st.columns([1.1, 1], gap="large")
    with readiness_col:
        render_panel(
            "Readiness",
            (
                f"Question guide: <strong>{'ready' if questions else 'missing'}</strong><br>"
                f"Personas: <strong>{len(persona_files)}</strong><br>"
                f"Completed AI interviews: <strong>{len(ai_files)}</strong>"
            ),
        )
    with action_col:
        render_panel(
            "Why This Matters",
            (
                "AI responses in this kind of workflow can feel polished but repetitive. "
                "This workspace makes it easier to run multiple personas, then immediately inspect whether each transcript actually feels distinct."
            ),
        )
        active_protocol = st.session_state.study_settings.get("protocol_name", "unsaved protocol")
        st.caption(f"Active protocol: {active_protocol}")

    if not questions:
        st.warning("Load the interview guide in Study Design before simulating interviews.")
    elif not persona_files:
        st.warning("Create at least one persona in Persona Studio before simulating interviews.")
    else:
        selected_names = st.multiselect(
            "Choose personas to simulate",
            options=[path.name for path in persona_files],
            default=[path.name for path in persona_files],
        )
        selected_paths = [PERSONAS_DIR / name for name in selected_names]

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Run selected simulations", use_container_width=True):
                simulate_selected_personas(selected_paths)
                st.rerun()
        with col2:
            if st.button("Run missing simulations only", use_container_width=True):
                missing = [
                    persona_path
                    for persona_path in persona_files
                    if not (AI_RESPONSES_DIR / f"{persona_path.stem}_responses.json").exists()
                ]
                simulate_selected_personas(missing)
                st.rerun()

        status_rows = []
        for persona_path in persona_files:
            response_path = AI_RESPONSES_DIR / f"{persona_path.stem}_responses.json"
            status_rows.append(
                {
                    "persona": persona_path.stem.replace("_", " ").title(),
                    "status": "Ready" if response_path.exists() else "Not run",
                    "file": response_path.name if response_path.exists() else "-",
                }
            )
        st.dataframe(status_rows, use_container_width=True, hide_index=True)

        if ai_files:
            preview_file = st.selectbox(
                "Preview AI interview",
                options=[path.name for path in ai_files],
                index=0,
            )
            preview_path = AI_RESPONSES_DIR / preview_file
            preview_data = load_ai_interview(preview_path)
            st.session_state.last_previewed_ai_file = preview_file
            with st.expander("Transcript preview", expanded=True):
                for item in preview_data[:5]:
                    st.markdown(f"**Q:** {item['question']}")
                    st.markdown(f"**A:** {item['answer']}")
                    st.markdown("---")
            st.download_button(
                "Download AI interview JSON",
                data=preview_path.read_bytes(),
                file_name=preview_path.name,
                mime="application/json",
                key=f"download_{preview_path.name}",
            )


with tab4:
    st.markdown("### Analysis Studio")
    st.caption(
        "Compare real and AI-generated interviews, generate Gioia-style outputs, and export transcripts for reporting."
    )

    real_ready = REAL_TRANSCRIPT_PATH.exists()
    ai_files = get_ai_response_files()

    top_col1, top_col2 = st.columns([1.1, 1], gap="large")
    with top_col1:
        render_panel(
            "Analysis Lens",
            (
                "In many qualitative comparison workflows, whole-interview interpretation is more useful than rigid question-by-question matching. "
                "The prompts here therefore ask for structured comparison while still looking across the broader conversation."
            ),
        )
    with top_col2:
        render_panel(
            "Available Materials",
            (
                f"Real transcript: <strong>{'ready' if real_ready else 'missing'}</strong><br>"
                f"AI interviews: <strong>{len(ai_files)}</strong><br>"
                f"Saved analyses: <strong>{len(list(OUTPUTS_DIR.glob('*.md')))}</strong>"
            ),
        )

    if not real_ready or not ai_files:
        st.warning(
            "Load a real transcript and generate at least one AI interview before running comparative analysis."
        )
    else:
        selected_ai_name = st.selectbox(
            "Choose AI interview for analysis",
            options=[path.name for path in ai_files],
            index=0,
        )
        selected_ai_path = AI_RESPONSES_DIR / selected_ai_name
        comparison_base_name = f"comparison_analysis_{selected_ai_path.stem}"
        structured_path = OUTPUTS_DIR / f"{comparison_base_name}.json"
        if structured_path.exists() and st.session_state.latest_comparison_key != selected_ai_name:
            st.session_state.latest_comparison_structured = json.loads(structured_path.read_text(encoding="utf-8"))
            st.session_state.latest_comparison_key = selected_ai_name
        elif not structured_path.exists() and st.session_state.latest_comparison_key != selected_ai_name:
            st.session_state.latest_comparison_structured = None
            st.session_state.latest_comparison_key = selected_ai_name

        action_cols = st.columns(3)
        with action_cols[0]:
            if st.button("Run comparison analysis", use_container_width=True):
                with st.spinner("Comparing real and AI interviews..."):
                    structured_comparison = run_structured_comparison(selected_ai_path)
                if structured_comparison:
                    save_structured_comparison(comparison_base_name, structured_comparison)
                    st.session_state.latest_comparison_structured = structured_comparison
                    st.session_state.latest_comparison = structured_comparison.get("markdown_report", "")
                    st.session_state.latest_comparison_key = selected_ai_name
                    st.success("Structured comparison analysis generated.")
                else:
                    with st.spinner("Falling back to markdown comparison analysis..."):
                        comparison_analysis = run_comparison(selected_ai_path)
                    comparison_path = OUTPUTS_DIR / f"{comparison_base_name}.md"
                    save_markdown(
                        comparison_path,
                        f"Real vs AI Interview Comparison ({selected_ai_name})",
                        comparison_analysis,
                    )
                    st.session_state.latest_comparison = comparison_analysis
                    st.session_state.latest_comparison_key = selected_ai_name
                    st.error("Structured comparison parsing failed, but a markdown comparison was saved.")
        with action_cols[1]:
            if st.button("Analyze real interview", use_container_width=True):
                with st.spinner("Running Gioia analysis on the real transcript..."):
                    real_analysis = run_real_interview_analysis()
                real_analysis_path = OUTPUTS_DIR / "real_interview_analysis.md"
                save_markdown(real_analysis_path, "Real Interview Gioia Analysis", real_analysis)
                st.session_state.latest_real_analysis = real_analysis
                st.success("Real interview analysis generated.")
        with action_cols[2]:
            if st.button("Analyze selected AI interview", use_container_width=True):
                ai_analysis_path = OUTPUTS_DIR / f"{selected_ai_path.stem}_gioia.md"
                with st.spinner("Running Gioia analysis on the AI interview..."):
                    ai_analysis = analyze_gioia(
                        str(selected_ai_path), str(ai_analysis_path), settings=st.session_state.study_settings
                    )
                st.session_state.latest_ai_analysis = ai_analysis
                st.success("AI interview analysis generated.")

        st.divider()

        if st.session_state.latest_comparison_structured:
            structured = st.session_state.latest_comparison_structured
            compare_tab, quotes_tab, themes_tab, narrative_tab = st.tabs(
                ["Comparison Matrix", "Quote Review", "Theme Review", "Narrative Report"]
            )

            with compare_tab:
                overview = structured.get("overview", {})
                summary_cols = st.columns(3)
                summary_cols[0].metric("Real Interview", "Loaded")
                summary_cols[1].metric("AI Interview", selected_ai_path.stem.replace("_", " ").title())
                summary_cols[2].metric("Themes Compared", len(structured.get("comparison_table", [])))
                if overview.get("key_takeaway"):
                    render_research_note(overview.get("key_takeaway", ""))
                comparison_rows = structured.get("comparison_table", [])
                if comparison_rows:
                    st.dataframe(comparison_rows, use_container_width=True, hide_index=True)

            with quotes_tab:
                quote_cols = st.columns(2)
                real_quotes = structured.get("quotes", {}).get("real", [])
                ai_quotes = structured.get("quotes", {}).get("ai", [])
                with quote_cols[0]:
                    st.markdown("#### Real Interview Quotes")
                    if real_quotes:
                        st.dataframe(real_quotes, use_container_width=True, hide_index=True)
                    else:
                        st.info("No real interview quotes extracted yet.")
                with quote_cols[1]:
                    st.markdown("#### AI Interview Quotes")
                    if ai_quotes:
                        st.dataframe(ai_quotes, use_container_width=True, hide_index=True)
                    else:
                        st.info("No AI interview quotes extracted yet.")

            with themes_tab:
                theme_items = structured.get("theme_review", [])
                if theme_items:
                    for idx, item in enumerate(theme_items):
                        note_key = f"{selected_ai_path.stem}_theme_{idx}"
                        with st.expander(f"{item.get('dimension', 'Dimension')} -> {item.get('theme', 'Theme')}", expanded=idx == 0):
                            st.markdown(f"**First-order concepts:** {', '.join(item.get('first_order_concepts', []))}")
                            st.markdown(f"**Real evidence:** {item.get('real_evidence', '')}")
                            st.markdown(f"**AI evidence:** {item.get('ai_evidence', '')}")
                            st.markdown(f"**Model note:** {item.get('review_note', '')}")
                            reviewer_note = st.text_area(
                                "Researcher review note",
                                value=st.session_state.theme_review_notes.get(note_key, ""),
                                key=note_key,
                                height=100,
                            )
                            st.session_state.theme_review_notes[note_key] = reviewer_note
                    relevant_notes = {
                        key: value
                        for key, value in st.session_state.theme_review_notes.items()
                        if key.startswith(f"{selected_ai_path.stem}_theme_")
                    }
                    st.download_button(
                        "Download theme review notes",
                        data=json.dumps(relevant_notes, indent=2),
                        file_name=f"{selected_ai_path.stem}_theme_review_notes.json",
                        mime="application/json",
                        key=f"theme_notes_download_{selected_ai_path.stem}",
                    )
                else:
                    st.info("Run a comparison analysis to populate theme review.")

            with narrative_tab:
                if structured.get("markdown_report"):
                    st.markdown(structured.get("markdown_report", ""))
                else:
                    st.info("No narrative report available yet.")

        else:
            analysis_choice = st.radio(
                "Analysis preview",
                ["Latest comparison", "Latest real interview analysis", "Latest AI interview analysis"],
                horizontal=True,
            )
            if analysis_choice == "Latest comparison" and st.session_state.latest_comparison:
                st.markdown(st.session_state.latest_comparison)
            elif analysis_choice == "Latest real interview analysis" and st.session_state.latest_real_analysis:
                st.markdown(st.session_state.latest_real_analysis)
            elif analysis_choice == "Latest AI interview analysis" and st.session_state.latest_ai_analysis:
                st.markdown(st.session_state.latest_ai_analysis)
            else:
                st.info("Run an analysis to preview it here.")

        st.divider()
        st.markdown("#### Exports")
        export_cols = st.columns(2)
        with export_cols[0]:
            if st.button("Export selected AI interview in all formats", use_container_width=True):
                export_all_formats(str(selected_ai_path), selected_ai_path.stem, output_dir=str(EXPORTS_DIR))
                st.success("Interview exported to DOCX, PDF, CSV, TXT, and HTML.")
        with export_cols[1]:
            if st.button("Refresh saved outputs", use_container_width=True):
                st.rerun()

        saved_output_files = sorted(
            [path for path in OUTPUTS_DIR.iterdir() if path.is_file() and path.suffix in {".md", ".json", ".csv", ".html"}]
        )
        if saved_output_files:
            chosen_output = st.selectbox(
                "Download a saved comparison or analysis output",
                options=[path.name for path in saved_output_files],
            )
            chosen_output_path = OUTPUTS_DIR / chosen_output
            output_mime = "text/plain"
            if chosen_output_path.suffix == ".json":
                output_mime = "application/json"
            elif chosen_output_path.suffix == ".csv":
                output_mime = "text/csv"
            elif chosen_output_path.suffix == ".html":
                output_mime = "text/html"
            elif chosen_output_path.suffix == ".md":
                output_mime = "text/markdown"
            st.download_button(
                "Download selected output",
                data=chosen_output_path.read_bytes(),
                file_name=chosen_output_path.name,
                mime=output_mime,
                key=f"download_output_{chosen_output}",
            )

        exported_docs = sorted(EXPORTS_DIR.glob("*"))
        if exported_docs:
            chosen_export = st.selectbox(
                "Download an exported transcript",
                options=[path.name for path in exported_docs],
            )
            chosen_export_path = EXPORTS_DIR / chosen_export
            mime = "application/octet-stream"
            if chosen_export_path.suffix == ".pdf":
                mime = "application/pdf"
            elif chosen_export_path.suffix == ".docx":
                mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            st.download_button(
                "Download exported file",
                data=chosen_export_path.read_bytes(),
                file_name=chosen_export_path.name,
                mime=mime,
                key=f"download_export_{chosen_export}",
            )
