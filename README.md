# Qualitative AI Interview Studio

A Streamlit application for examining qualitative interview workflows that compare real interview transcripts with persona-based AI interview simulations.

This repository presents a research-oriented tool rather than a general-purpose chatbot or a production data platform. Its purpose is to support methodological exploration around the use of AI in interview-based qualitative research, especially in cases where a researcher wants to compare AI-generated interview material against real interview data using a shared interview guide.

## Research Purpose

The central methodological question behind this project is:

`How can AI-generated interview material be examined alongside real interview material in a structured qualitative workflow?`

The application is intended to support inquiry into issues such as:

- the degree to which AI-generated interviews resemble or diverge from real interviews
- whether persona-conditioned prompting yields data that is analytically useful
- where AI-generated responses become overly generic, overly polished, or insufficiently grounded in lived context
- how AI may assist with early-stage qualitative comparison without replacing interpretive judgment

Rather than assuming AI output is either valid by default or invalid by default, the tool is designed to make differences visible and reviewable.

## Scope Of The Application

The application supports a bounded qualitative workflow:

- upload a real interview transcript
- upload or extract a shared interview guide
- create participant personas from text or documents
- simulate AI interviews from those personas
- compare real and AI-generated interview material
- review differences through tables, quotes, themes, and narrative outputs
- export interview and analysis artifacts

This workflow is particularly relevant to exploratory studies of AI-assisted qualitative methods, synthetic respondent workflows, and comparative evaluation of interview outputs.

## Intended Users

This project is most likely to be useful for:

- qualitative researchers
- interview-based management and social science researchers
- doctoral students and faculty working with qualitative methods
- market, organizational, and UX researchers using semi-structured interviews
- researchers investigating AI-supported methodological workflows

## Current Analytical Structure

The application is organized into four sections:

- `Study Design`
  Researchers upload a real transcript, upload an interview guide, and define a simple study protocol to guide simulation and analysis.

- `Persona Studio`
  Researchers create personas from manual descriptions or uploaded source documents and review extracted fields before saving.

- `Simulation Lab`
  Researchers run persona-conditioned AI interviews using the shared guide and inspect generated responses.

- `Analysis Studio`
  Researchers compare real and AI interview material, review extracted quotes and themes, generate Gioia-style outputs, and export files.

## Current Features

- transcript upload in `txt`, `docx`, and `pdf`
- interview guide upload in `txt` and `pdf`
- persona creation from text, `docx`, or `pdf`
- persona-conditioned AI interview simulation
- reusable study protocol fields:
  - `Shared study context`
  - `Interview style guidance`
  - `Consistency rules`
  - `Analysis focus`
- structured comparison review through:
  - `Comparison Matrix`
  - `Quote Review`
  - `Theme Review`
  - `Narrative Report`
- Gioia-style analysis generation
- researcher-authored notes within theme review
- export support for AI interview transcripts in `docx`, `pdf`, `csv`, `txt`, and `html`

## Methodological Orientation

The design of the application reflects several methodological commitments:

- AI-generated material should be reviewable rather than taken at face value.
- Persona conditioning should be explicit and inspectable.
- Shared interview guides matter for comparability across real and simulated interviews.
- Differences in specificity, emotional texture, context, and interpretive richness are analytically important.
- AI can be useful as an augmentative device without functioning as a substitute for qualitative interpretation.

The application should therefore be understood as a methodological aid for comparison, exploration, and reflective analysis, not as an automated replacement for qualitative research practice.

## Deployment Status

At its current stage, the application is suitable for:

- pilot deployment
- demonstrations
- exploratory use by a small number of researchers
- early-stage methodological testing

It is not yet intended as:

- a production multi-user platform
- a persistent collaborative research environment
- a full research project management system

For the practical question, `Can this be deployed so researchers can try it online?`, the answer is yes.

## Technical Stack

- Streamlit
- OpenAI API
- Python
- `python-docx`
- `PyPDF2`
- `pdfplumber`
- `pymupdf`
- `fpdf2`

## Repository Structure

```text
app.py
config.py
requirements.txt
run.sh
install.py

personas/
questions/
study_protocols/
data/
  ai_responses/
outputs/
exports/

scripts/
  simulate_interviews.py
  analyze_gioia.py
  export_results.py

utils/
  pdf_parser.py
  persona_parser.py
```

## Local Setup

Recommended:

```bash
python install.py
./run.sh
```

Manual setup:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Environment Configuration

Set `OPENAI_API_KEY` through one of the following:

- shell environment variable
- `.env`
- Streamlit secrets

Example:

```bash
export OPENAI_API_KEY="your-key-here"
```

## Deployment

The simplest deployment path is Streamlit Community Cloud.

High-level deployment steps:

1. Push the repository to GitHub.
2. Create a Streamlit app from the repository.
3. Set `app.py` as the entry point.
4. Add `OPENAI_API_KEY` in Streamlit secrets.
5. Deploy.

## Current Limitations

- model outputs are variable across runs
- AI-generated interviews may become repetitive when persona inputs are thin
- local file storage is convenient but not persistent across all hosting environments
- PDF extraction quality depends on source file quality
- the current system is better suited to individual or light pilot use than sustained collaborative research use

## Appropriate Uses

- methodological experimentation with AI-assisted qualitative workflows
- comparison of real and AI-generated interview material
- pilot testing of interview guides
- production of structured comparison artifacts for analytic reflection
- early-stage thematic and Gioia-style scaffolding

## Less Appropriate Uses

- replacing human qualitative interpretation
- large-scale collaborative project management
- long-term persistent storage without added infrastructure
- high-stakes use cases that require deterministic outputs

## Future Directions

- local named workspaces
- persistent study storage
- collaborative annotation
- stronger project-level organization
- richer review workflows around quotes and themes

## License

Add the license you want if you plan to distribute the repository publicly.
