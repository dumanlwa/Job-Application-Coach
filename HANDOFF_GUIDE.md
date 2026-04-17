# Job Application Coach - Comprehensive Project Handoff Guide

This document is a full technical handoff for writing a project report, demonstrating the system, and running it in both live LLM mode and mock mode.

## 1) What this project is

This project is a Flask-based multi-agent backend (with a lightweight web UI) that helps tailor a CV for a target job. The system accepts a job description and CV text, then runs a sequential pipeline of specialized agents to produce five outputs: structured job analysis, resume-gap analysis, rewritten CV, cover letter, and a final scoring report.

At a high level, the architecture separates concerns into four layers: the API layer (`app.py`) for validation and endpoints, the orchestration layer (`services/coach_service.py`) for agent sequencing, the model-access layer (`services/llm_client.py`) for provider-specific LLM calls, and persistence/testing utilities (`services/file_storage.py`, `services/storage.py`, `services/mock_agent_loader.py`) for reproducibility and inspection.

## 2) End-to-end architecture (multi-agent)

The pipeline is intentionally ordered so each downstream agent receives richer context from previous steps:

1. Job Analyzer
2. Resume Matcher
3. Rewrite Coach
4. Cover Letter
5. Scoring and Feedback

The dependency chain is strict for full-analysis mode:

- Job Analyzer consumes `job_description` (and optionally the CV text packaged in the prompt input helper).
- Resume Matcher consumes `resume_text` plus either `job_analysis` (preferred) or raw `job_description`.
- Rewrite Coach consumes `resume_text` + `resume_match` (+ optional `bullets`, `target_role`).
- Cover Letter consumes `updated_cv` (+ optional `job_analysis`, `resume_match`).
- Scoring consumes `updated_cv` (+ optional `job_analysis`, `resume_match`).

This design gives each agent a narrow role, improving consistency and debuggability compared with one monolithic prompt.

## 3) Repository map and what each file/folder does

### Root-level application files

- `app.py`: Flask application factory, input validation, endpoint registration, centralized error handling.
- `requirements.txt`: Python dependencies (`Flask`, `flask-cors`, `python-dotenv`, `requests`).
- `.env.example`: baseline environment configuration template.
- `.env`: runtime configuration (created by user from `.env.example`).
- `README.md`: quick-start usage documentation.
- `test_client.py`: integration-style script that calls `/api/health` and `/api/full-analysis`.

### Service layer (`services/`)

- `services/coach_service.py`: main orchestrator; executes agents, prepares context, stores outputs, and supports mock loading.
- `services/prompts.py`: all agent system prompts are centralized here.
- `services/llm_client.py`: provider adapter for OpenAI-compatible and Gemini APIs.
- `services/json_utils.py`: robust JSON parsing/cleanup for imperfect LLM outputs.
- `services/mock_agent_loader.py`: deterministic test mode loader for pre-recorded agent outputs.
- `services/file_storage.py`: file-based run/agent artifact persistence.
- `services/storage.py`: SQLite persistence alternative.

### Frontend/UI

- `templates/index.html`: single-page UI shell.
- `static/app.js`: front-end request/response wiring and result rendering.
- `static/styles.css`: visual styling for the UI.

### Generated artifacts (runtime)

- `run_<run_id>.json`: run-level metadata.
- `agent_<run_id>_<agent_name>_001.json`: per-agent saved input/output + parsed JSON + duration.
- `coach.db`: SQLite database file if SQLite storage mode is enabled.

### Example data files in this repo

- `cv_data_analyst.txt`, `cv_data_engineer.txt`, `cv_data_scientist.txt` and matching `.docx` files: sample CV inputs used during development/testing.

## 4) API endpoints and I/O contracts

### Health

- `GET /api/health`
- Purpose: service liveness check.

### Job Analyzer

- `POST /api/job-analyzer`
- Required: `job_description`
- Optional: `resume_text` or `cv_text`
- Output: `job_analysis`

### Resume Matcher

- `POST /api/resume-matcher`
- Required: `resume_text` (or `cv_text`)
- Required: one of `job_analysis` or `job_description`
- Output: `resume_match`

### Rewrite Coach

- `POST /api/rewrite-coach`
- Required: `resume_text` (or `cv_text`), `resume_match`
- Optional: `bullets`, `target_role`
- Output: `updated_cv` (plain text CV only)

### Cover Letter

- `POST /api/cover-letter`
- Required: `updated_cv`
- Optional: `job_analysis`, `resume_match`
- Output: `cover_letter`

### Scoring

- `POST /api/scoring`
- Required: `updated_cv`
- Optional: `job_analysis`, `resume_match`
- Output: `scoring` JSON with overall + components + recommendations

### Full pipeline

- `POST /api/full-analysis`
- Required: `job_description`, `resume_text` (or `cv_text`)
- Optional: `bullets`, `target_role`
- Output: combined payload with `run_id`, `job_analysis`, `resume_match`, `updated_cv`, `cover_letter`, `scoring`

## 5) Prompt system and where prompts are stored

All agent prompts are in `services/prompts.py` as constants:

- `JOB_ANALYZER_PROMPT`
- `RESUME_MATCHER_PROMPT`
- `REWRITE_COACH_PROMPT`
- `COVER_LETTER_PROMPT`
- `SCORING_FEEDBACK_PROMPT`

Why this matters for a report: this centralization makes prompt governance easier (auditing, versioning, and controlled updates). It also makes behavior changes explicit and low-risk.

Current scoring behavior note: `SCORING_FEEDBACK_PROMPT` includes explicit leniency guidance for `keyword_coverage` and `role_alignment` so the scoring agent does not over-penalize near matches, transferable skills, or semantic equivalents.

## 6) Setup from scratch

1) Create and activate a virtual environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) Install dependencies.

```powershell
pip install -r requirements.txt
```

3) Create environment file.

```powershell
Copy-Item .env.example .env
```

4) Edit `.env` according to run mode (live or mock details below).

## 7) Running in original (live LLM) mode

Live mode means agent outputs come from a real LLM provider.

### Option A: OpenAI-compatible provider

Set in `.env`:

```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=<your_api_key>
LLM_TIMEOUT_SECONDS=90
```

### Option B: Gemini provider

Set in `.env`:

```env
LLM_PROVIDER=gemini
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta
LLM_MODEL=gemini-2.0-flash
LLM_API_KEY=<your_google_ai_api_key>
LLM_TIMEOUT_SECONDS=90
```

Then start the backend:

```powershell
python app.py
```

Expected base URL: `http://localhost:5000`

UI entry point: `GET /`.

## 8) Running in mock mode (no live LLM calls)

Mock mode uses previously saved agent files and bypasses external LLM calls. This is ideal for demos, reproducibility, offline testing, and report screenshots.

Set environment variables before starting the app:

```powershell
$env:COACH_MOCK_RUN_ID="20260408T052936056338"
$env:COACH_MOCK_DATA_DIR="."
python app.py
```

How it works internally:

- `services/mock_agent_loader.py` checks `COACH_MOCK_RUN_ID`.
- For each agent invocation, it loads `agent_<run_id>_<agent_name>_001.json`.
- If a required mock file is missing, the request fails with a clear error.

To return to live mode in the current terminal session:

```powershell
Remove-Item Env:COACH_MOCK_RUN_ID -ErrorAction SilentlyContinue
Remove-Item Env:COACH_MOCK_DATA_DIR -ErrorAction SilentlyContinue
python app.py
```

## 9) Storage and run logging behavior

The app supports two storage backends via `COACH_STORAGE`.

### File mode (default)

- Set: `COACH_STORAGE=file`
- Optional path: `COACH_FILE_STORAGE_PATH=.`
- Writes JSON artifacts directly to configured folder.

### SQLite mode

- Set: `COACH_STORAGE=sqlite`
- Optional DB path: `COACH_DB_PATH=coach.db`
- Stores runs and agent calls in relational tables.

In both modes, each agent call includes input text, output text, parsed JSON (if applicable), and execution duration for traceability.

## 10) Request processing sequence (what happens at runtime)

When `/api/full-analysis` is called, the backend performs the following sequence in `services/coach_service.py`:

1. Creates one run record (`run_id`) so all agent calls are grouped.
2. Calls Job Analyzer and parses JSON output.
3. Calls Resume Matcher using Job Analyzer output context.
4. Calls Rewrite Coach using Resume Matcher output context.
5. Calls Cover Letter using rewritten CV + prior context.
6. Calls Scoring using rewritten CV + prior context.
7. Returns combined response payload.
8. Persists every call’s input/output metadata.

If JSON parsing fails for an expected JSON response, `services/json_utils.py` attempts fence stripping, quote normalization, newline normalization, nested parse recovery, and object/array extraction. If still invalid, it returns `{"raw_output": ...}` to preserve visibility rather than failing silently.

## 11) Error handling model

Error handling is centralized in `app.py`:

- Input contract errors raise `ValueError` and return HTTP 400.
- Runtime/LLM errors raise `RuntimeError` and return HTTP 500.
- Unexpected exceptions return HTTP 500 with a generic message.

`services/coach_service.py` also attempts to save failed agent calls so failures remain auditable.

## 12) How to test quickly

### Quick health test

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:5000/api/health
```

### Full pipeline test using provided script

```powershell
python test_client.py
```

`test_client.py` performs:

- `GET /api/health`
- `POST /api/full-analysis` with sample job/CV payload
- basic response key checks and summary prints

For a deterministic test, run the server in mock mode first.

## 13) Practical guidance for writing the report

A strong report sectioning for this project is: Problem and Motivation, System Architecture, Agent Design Rationale, Prompt Engineering Strategy, API and Data Contracts, Storage and Reproducibility, Testing Strategy, Limitations, and Future Improvements.

For limitations, mention that output quality still depends on upstream LLM behavior and prompt adherence. For future work, mention async execution, retry/backoff in the LLM client, stricter schema validation, and observability dashboards.

## 14) Common troubleshooting

If you see `LLM_API_KEY is not set`, verify `.env` is loaded and key variable matches provider mode.

If you see 503 or provider transient errors in live mode, retry the request or switch to mock mode for demos/report work.

If mock mode fails with "file not found", ensure `COACH_MOCK_RUN_ID` matches the exact run artifact prefix available in your project folder.

If endpoint responses are missing sections, inspect saved `agent_*` files to confirm whether the issue is model output quality or parser fallback behavior.

## 15) Reproducible demo checklist (for your friend)

1. Clone/copy the project.
2. Create virtual environment and install requirements.
3. Configure `.env`.
4. Choose mode:
   - Live mode for realistic generation, or
   - Mock mode for deterministic demonstration.
5. Start `python app.py`.
6. Open `http://localhost:5000` and run one full analysis.
7. Capture generated JSON artifacts and screenshots for the report.

This checklist gives both scientific reproducibility (mock) and practical realism (live).