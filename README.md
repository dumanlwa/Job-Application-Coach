# Job Application Coach - Flask Backend

For a full project handoff (architecture, run modes, I/O flow, file-by-file explanation, and report-writing guidance), see `HANDOFF_GUIDE.md`.

This backend exposes REST APIs for the Job Application Coach system:
- Job Analyzer Agent
- Resume Matcher Agent
- Rewrite Coach Agent
- Cover Letter Agent
- Scoring and Feedback Agent
- Full analysis pipeline

Agent dependency chain:
1. Job Analyzer takes `job_description`.
2. Resume Matcher takes Job Analyzer output (`job_analysis`) + `resume_text`.
3. Rewrite Coach takes Resume Matcher output (`resume_match`) + `resume_text`.
4. Rewrite Coach returns only `updated_cv` (full updated CV text).
5. Cover Letter takes `updated_cv` (optionally plus `job_analysis` and `resume_match`).
6. Scoring takes `updated_cv` (optionally plus `job_analysis` and `resume_match`).

For end users, the main pipeline still starts with only two inputs: `job_description` and `resume_text` via `/api/full-analysis`.

## 1) Setup

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set your LLM values.

## 2) Run

```bash
python app.py
```

Server runs on `http://localhost:5000` by default.

Frontend is available at:
- `GET /` -> `http://localhost:5000/`

The page submits `job_description` and `cv_text` to `/api/full-analysis` and renders:
- job analysis
- resume match
- updated CV
- cover letter
- scoring feedback

## 3) API Endpoints

- `GET /api/health`
- `POST /api/job-analyzer`
- `POST /api/resume-matcher`
- `POST /api/rewrite-coach`
- `POST /api/cover-letter`
- `POST /api/scoring`
- `POST /api/full-analysis`

### Sample Request JSON

```json
{
  "job_description": "Paste full job posting...",
  "resume_text": "Paste resume text...",
  "bullets": ["Built a dashboard for ...", "Analyzed customer churn ..."],
  "target_role": "data scientist"
}
```

### Endpoint Input Contracts

- `POST /api/job-analyzer`
  - Required: `job_description`

- `POST /api/resume-matcher`
  - Required: `resume_text`
  - Required: one of `job_analysis` (preferred) or `job_description` (fallback)

- `POST /api/rewrite-coach`
  - Required: `resume_text`, `resume_match`
  - Optional: `bullets`, `target_role`
  - Output: `updated_cv` only

- `POST /api/cover-letter`
  - Required: `updated_cv`
  - Optional: `job_analysis`, `resume_match`

- `POST /api/scoring`
  - Required: `updated_cv`
  - Optional: `job_analysis`, `resume_match`

- `POST /api/full-analysis`
  - Required: `job_description`, `resume_text`
  - Optional: `bullets`, `target_role`

## 4) LLM Configuration

OpenAI-compatible setup:
- `LLM_PROVIDER=openai`
- `LLM_BASE_URL=https://api.openai.com/v1`
- `LLM_MODEL=gpt-4o-mini`

Gemini setup:
- `LLM_PROVIDER=gemini`
- `LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta`
- `LLM_MODEL=gemini-2.0-flash`
- `LLM_API_KEY=<your_google_ai_api_key>`

Optional output-length controls:
- `LLM_MAX_TOKENS=3200` (increase if outputs are cut off)
- `LLM_MAX_CONTINUATIONS=3` (auto-continue when provider stops with length limit)

## 5) Mock Testing (No Live LLM Calls)

You can test the full pipeline using existing saved agent outputs.

Mock loading logic is isolated in a dedicated testing module:
- `services/mock_agent_loader.py`

Set these env variables before starting the API:

```powershell
$env:COACH_MOCK_RUN_ID="20260330T165023420112"
$env:COACH_MOCK_DATA_DIR="."
.\.venv\Scripts\python.exe app.py
```

In mock mode, each agent call reads:
- `agent_<run_id>_job_analyzer_001.json`
- `agent_<run_id>_resume_matcher_001.json`
- `agent_<run_id>_rewrite_coach_001.json`
- `agent_<run_id>_cover_letter_001.json`
- `agent_<run_id>_scoring_001.json`

No LLM API request is made when mock files are available.

## 6) Notes

- If the model returns non-JSON text for JSON endpoints, the API returns it under `raw_output`.

## File-based storage

The backend saves explicit JSON files for each agent call by default. Files are written directly in the project root (or your configured folder).

Generated file examples:
- `run_<run_id>.json`
- `agent_<run_id>_job_analyzer_001.json`
- `agent_<run_id>_resume_matcher_001.json`
- `agent_<run_id>_rewrite_coach_001.json`
- `agent_<run_id>_cover_letter_001.json`
- `agent_<run_id>_scoring_001.json`

Enable by setting in your `.env`:

```
COACH_STORAGE=file
# optional: change base path
COACH_FILE_STORAGE_PATH=.
```

Then restart the server. Files will be created under the specified folder.
