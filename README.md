# AI vs. Real Interview Comparison (Streamlit)

A Streamlit app for **qualitative interview research** that:

1. Ingests a **human interview transcript** and an **interview guide** (questions as plain text or extracted from a PDF).
2. Defines **synthetic participant personas** (manual text or PDF/DOCX), then **simulates** how a large language model answers the same questions in character.
3. Produces **Gioia-style** thematic comparisons—first-order concepts, themes, and aggregate dimensions—contrasting real vs. AI-generated material, with exports to Markdown, DOCX, and PDF.

It is aimed at workflows where you want a structured, reproducible way to probe **what LLM-based “participants” say** next to **actual interview data**, using familiar qualitative coding language rather than ad hoc summaries alone.

## What you need

- **Python 3.10+** (3.11/3.12 recommended).
- An **OpenAI API key** with access to the Chat Completions API (the app uses `gpt-3.5-turbo` by default in the codebase).

## Quick start (local)

```bash
git clone <your-fork-or-repo-url>
cd custom-gpt-interview-research

# Optional helper: creates .venv and installs dependencies
python install.py
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Or manually:
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Configure the API key **either**:

- **Environment variable:** `export OPENAI_API_KEY="sk-..."`, or a `.env` file in the project root with `OPENAI_API_KEY=...` (loaded via `python-dotenv`), **or**
- **Streamlit secrets** (recommended on [Streamlit Community Cloud](https://streamlit.io/cloud)): add `OPENAI_API_KEY` in *App settings → Secrets*.

Run the app:

```bash
streamlit run app.py
```

Or: `./run.sh` (expects `.venv` or `venv`).

Open the URL shown in the terminal (default `http://localhost:8501`).

## Using the four tabs

| Tab | Purpose |
|-----|---------|
| **Upload Real Interview** | Upload the **real transcript** (TXT, PDF, or DOCX). Upload **questions** as `.txt` (one per line) or `.pdf` (text is extracted, then questions are inferred with the API). |
| **Add Personas** | Create personas from **manual description** or **PDF/DOCX**; the app uses the API to normalize fields (name, role, personality, etc.) and saves JSON under `personas/`. |
| **Simulate AI Interviews** | For each persona JSON, runs **simulated answers** and writes `data/ai_responses/<persona>_responses.json`. |
| **Compare & Analyze** | Runs **real vs. AI** comparison and optional **Gioia-style** analyses; download Markdown analyses; export simulated interviews to **DOCX/PDF** under `exports/`. |

## Repository layout

```
app.py                 # Streamlit entrypoint
config.py              # OPENAI_API_KEY: st.secrets → .env / environment
utils/
  pdf_parser.py       # PDF text + AI question extraction
  persona_parser.py   # DOCX/PDF persona text + AI structuring
scripts/
  simulate_interviews.py
  analyze_gioia.py
  export_results.py
personas/              # Persona JSON (repo keeps .gitkeep only)
questions/             # Saved questions.txt
data/
  ai_responses/       # Simulated interview JSON
  real_interview_transcript.txt   # Written when you upload a real transcript
outputs/               # Generated Markdown analyses
exports/               # DOCX/PDF exports from the Compare tab
```

Generated paths under `data/ai_responses`, `outputs`, `exports`, and `personas` are mostly **gitignored** except placeholder `.gitkeep` files—clone the repo clean and produce artifacts locally or on Streamlit Cloud’s ephemeral filesystem.

## PDF and DOCX behavior

- **Text must be selectable** in PDFs; scanned images need OCR elsewhere first.
- Extraction tries **pdfplumber**, then **PyMuPDF**, with **PyPDF2** as fallback—best-effort depending on how the PDF was produced.

## API usage and cost

Every step that calls the model (question extraction, persona parsing, simulation, Gioia analysis, comparison) consumes tokens. **Monitor usage** in the OpenAI dashboard. For production or heavy studies, consider upgrading models or batching in the code.

## Troubleshooting

- **“No OpenAI API key configured”** in the sidebar: set `OPENAI_API_KEY` via `.env`, shell, or Streamlit secrets.
- **Empty PDF text**: file may be image-only or protected; try export-to-text from your PDF tool.
- **Simulation errors**: confirm `questions/questions.txt` exists and persona JSON files are under `personas/`.

## Research context

Companion materials (e.g. presentation decks, interview scripts, and manuscripts such as *Yetim et al.*—Academy of Management–related qualitative work) live outside this repository. This codebase is the **implementation** of the workflow: **human transcript + shared questions + persona-conditioned LLM responses + Gioia-style comparison**.