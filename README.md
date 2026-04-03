# Qualitative AI Interview Studio

Qualitative AI Interview Studio is being built as a research platform for AI-assisted qualitative inquiry.

Its long-term purpose is not to generate polished demo transcripts. It is to give researchers a disciplined workspace for designing studies, simulating persona-based interviews, comparing AI-generated material against real interview data, and documenting where AI is useful, weak, biased, or methodologically risky.

The project is grounded in the NIU research context behind this repository: using a custom GPT-style workflow to compare persona-conditioned AI interviews with previously collected human interviews, then studying the differences through structured qualitative analysis.

## Vision

This repository is moving toward a platform where a researcher can:

- create a study workspace
- define a protocol with shared context, interview style guidance, consistency rules, and analysis focus
- build or extract personas from source material
- upload interview guides and real transcripts
- run AI interview simulations against the same semi-structured questions used with human participants
- compare human and AI transcripts through structured tables, quote review, theme review, and narrative synthesis
- generate analysis artifacts such as Gioia-style outputs and export-ready research documents
- preserve researcher control, auditability, and privacy throughout the workflow

The intended outcome is a serious methodological tool for research design, comparison, reflexivity, and validity checking, not a replacement for human interpretation.

## Research Direction

The NIU project framing behind this codebase is clear:

- AI may help researchers pilot interview protocols, test personas, surface patterned differences, and accelerate early-stage comparison work
- AI should be treated as a complementary method rather than a substitute for participants or for interpretive qualitative judgment
- the important question is not whether AI is "good" or "bad" for qualitative research in the abstract
- the important question is when it is useful, where it breaks down, and how those breakdowns become visible in a rigorous workflow

This platform is therefore being shaped around a research agenda that examines:

- thematic richness versus thematic flattening
- contextual specificity versus generic language
- emotional texture versus polished abstraction
- consistency versus drift across an interview
- analytic usefulness versus methodological distortion
- efficiency gains versus ethical and epistemic risk

## What This Will Become

The target product is a multi-surface research environment with a shared domain model across the app:

### 1. Study Workspace

A study-centered workspace will organize all major research assets:

- study records
- protocols
- personas
- question guides
- real transcripts
- AI simulations
- comparisons
- analytic outputs

The goal is for researchers to work inside a coherent project structure instead of juggling disconnected files, prompts, and exports.

### 2. Protocol Builder

Protocols will act as the methodological backbone of each study.

They will store the instructions that shape both generation and analysis, including:

- shared study context
- interview style guidance
- consistency rules
- analysis focus

This matters because the platform is meant to support repeatable research logic, not ad hoc prompting.

### 3. Persona Lab

The persona workflow will support the creation, extraction, refinement, and validation of interview personas from source documents.

Over time this should become a place to:

- ingest raw persona materials
- structure persona attributes and opinions
- retain original source text for traceability
- compare multiple persona variants
- study how persona quality affects AI interview quality

### 4. Interview Guide And Transcript Library

The platform is being shaped to accept interview guides and transcripts in researcher-friendly formats such as `txt`, `docx`, and `pdf`.

This layer will make it possible to:

- extract usable interview questions from uploaded material
- preserve real interview transcripts as comparison anchors
- reuse question guides across multiple simulations
- connect study assets without reformatting everything manually

### 5. Simulation Engine

The simulation layer will run persona-conditioned AI interviews using shared protocol guidance and reusable question guides.

The target experience is a controlled workflow where researchers can evaluate:

- whether AI stays in character
- whether answers remain concrete over time
- whether the model becomes too neat, too consistent, or too generic
- whether simulated material is useful for piloting, triangulation, or stress-testing a study design

### 6. Comparison And Analysis Workbench

The comparison workflow is one of the core reasons this project exists.

It is being built to help researchers inspect AI outputs against real interview material through:

- structured comparison matrices
- quote review
- theme review
- narrative summaries
- Gioia-oriented analytic scaffolding
- researcher-authored notes and interpretation

The platform should make differences visible rather than hiding them behind a single summary judgment.

### 7. Export And Reporting Layer

The long-term product should produce clean research artifacts that can move into papers, appendices, presentations, and internal review.

That includes exports for:

- transcripts
- comparison tables
- markdown and HTML summaries
- spreadsheet-compatible outputs
- printable research materials

## Product Principles

This project is being built around a few non-negotiable principles:

### AI As Augmentation

The system should support qualitative researchers without pretending to replace participants, fieldwork, or interpretation.

### Methodological Transparency

Researchers should be able to see what protocol, persona, prompt logic, and comparison frame produced a given result.

### Structured Comparison Over Hype

The platform should help users inspect strengths, misses, distortions, and implications instead of overselling AI realism.

### Privacy And Researcher Control

The NIU research context emphasizes careful handling of sensitive materials. The long-term platform should support private, controlled workflows rather than defaulting to broad data retention.

### Reusable Research Infrastructure

The goal is to turn a repetitive manual process into a repeatable research system that can support future studies, student researchers, conference outputs, and journal work.

## Architecture Direction

The repository already points toward the architecture this project is expected to grow into:

- a FastAPI backend for the research workflow and domain objects
- a browser-based frontend organized around studies and workspace pages
- a legacy prototype app retained in-repo but not used for the primary web runtime
- storage abstractions that can support local JSON today and Supabase-backed persistence later
- scripts for simulation, Gioia analysis, and exports
- parsers for common researcher document formats

That architecture is important because the end state is not a single prompt wrapper. It is a platform with separable workflow layers and a reusable API.

## Near-Term Roadmap

Based on the codebase and the NIU research trajectory, the next phase of the project is heading toward:

- a fuller study-first frontend that feels like a real research application
- more robust persistence for studies and outputs
- stronger authentication and user separation
- cleaner provenance around uploaded source materials and generated artifacts
- richer comparison views for human versus AI transcripts
- improved export workflows for presentations, papers, and appendix-ready materials
- better support for methodological notes, reflexive memos, and collaborative review
- stronger safeguards around privacy, traceability, and responsible AI use

## Who This Is For

The platform is being designed for:

- qualitative researchers
- management and organizational scholars
- market and consumer researchers
- doctoral students and faculty
- undergraduate researchers contributing to structured AI-methods projects
- teams exploring AI as a research support tool rather than a replacement for inquiry

## Current Repository As Foundation

Today’s repository should be understood as the foundation for that platform.

It already contains the major building blocks of the future system:

- backend models and API routes for studies, protocols, personas, guides, transcripts, simulations, analyses, comparisons, and exports
- a multi-page frontend scaffold organized around the intended research workflow
- a legacy prototype app that remains available for reference only
- storage and deployment scaffolding for local development and future hosted use

In other words, the codebase is no longer just experimenting with an idea. It is taking shape as research infrastructure.

## Local Development

Install dependencies:

```bash
python install.py
```

Run the current web app:

```bash
./run.sh
```

Run the FastAPI backend directly:

```bash
source .venv/bin/activate
python -m uvicorn backend.main:app --reload
```

The main environment variable required for AI-backed workflows is:

- `OPENAI_API_KEY`

Optional configuration supports storage and deployment setup:

- `STORAGE_BACKEND`
- `LOCAL_STORAGE_ROOT`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `CORS_ORIGINS`

## Repository Structure

```text
app.py                         # NiceGUI prototype for the research workflow
backend/                       # FastAPI app, schemas, services, storage
frontend/                      # Multi-page browser UI scaffold
scripts/                       # Simulation, analysis, and export logic
utils/                         # Parsers for txt, docx, and pdf research inputs
supabase/                      # Future persistence schema
backend_data/                  # Local JSON storage during development
```

## Status

The most useful way to read this repository is:

`a research platform under construction for AI-assisted qualitative comparison`

It is being built for where the work is going:

- from one-off prompting to reusable workflow
- from manual comparisons to structured analytic review
- from prototype tooling to research infrastructure
- from isolated experiments to a system that can support papers, presentations, and future studies

## License

Add the license that matches how you want to share or publish the project.
