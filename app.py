import os
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from services.coach_service import JobApplicationCoachService
from services.llm_client import LLMClient

load_dotenv()


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)
    asset_version = int(time.time())

    coach_service = JobApplicationCoachService(LLMClient())

    def json_error(message: str, status_code: int = 400):
        return jsonify({"error": message}), status_code

    def get_json_body():
        if not request.is_json:
            return None, json_error("Request must have Content-Type application/json.")

        body = request.get_json(silent=True)
        if body is None:
            return None, json_error("Invalid JSON body.")

        return body, None

    def require_text(body: dict, key: str) -> str:
        value = body.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"'{key}' is required and must be a non-empty string.")
        return value.strip()

    def optional_text(body: dict, key: str, default: str = "") -> str:
        value = body.get(key, default)
        if value is None:
            return default
        if not isinstance(value, str):
            raise ValueError(f"'{key}' must be a string when provided.")
        return value.strip()

    def required_text_from_keys(body: dict, keys: list, label: str) -> str:
        for key in keys:
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        joined = ", ".join(f"'{key}'" for key in keys)
        raise ValueError(f"{joined} is required and must be a non-empty string ({label}).")

    def optional_text_from_keys(body: dict, keys: list, default: str = "") -> str:
        for key in keys:
            value = body.get(key)
            if value is None:
                continue
            if not isinstance(value, str):
                raise ValueError(f"'{key}' must be a string when provided.")
            return value.strip()
        return default

    def optional_string_list(body: dict, key: str):
        value = body.get(key, [])
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError(f"'{key}' must be a list of strings.")

        cleaned = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                continue
            cleaned.append(item.strip())
        return cleaned

    def optional_json(body: dict, key: str):
        return body.get(key)

    def execute(handler):
        body, error = get_json_body()
        if error:
            return error

        try:
            result = handler(body)
            return jsonify(result), 200
        except ValueError as exc:
            return json_error(str(exc), 400)
        except RuntimeError as exc:
            return json_error(str(exc), 500)
        except Exception as exc:
            return json_error(f"Unexpected server error: {exc}", 500)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "job-application-coach"}), 200

    @app.get("/")
    def index():
        return render_template("index.html", asset_version=asset_version)

    @app.post("/api/job-analyzer")
    def job_analyzer():
        def handler(body):
            job_description = require_text(body, "job_description")
            resume_text = optional_text_from_keys(body, ["resume_text", "cv_text"], "")
            return coach_service.run_job_analyzer(job_description, resume_text)

        return execute(handler)

    @app.post("/api/resume-matcher")
    def resume_matcher():
        def handler(body):
            resume_text = required_text_from_keys(body, ["resume_text", "cv_text"], "CV text")
            job_analysis = optional_json(body, "job_analysis")
            job_description = optional_text(body, "job_description", "")

            if job_analysis is None and not job_description:
                raise ValueError("Provide either 'job_analysis' or 'job_description' for resume matching.")

            return coach_service.run_resume_matcher(
                resume_text,
                job_analysis=job_analysis,
                job_description=job_description,
            )

        return execute(handler)

    @app.post("/api/rewrite-coach")
    def rewrite_coach():
        def handler(body):
            resume_text = required_text_from_keys(body, ["resume_text", "cv_text"], "CV text")
            resume_match = optional_json(body, "resume_match")
            bullets = optional_string_list(body, "bullets")
            target_role = optional_text(body, "target_role", "data scientist")

            if resume_match is None:
                raise ValueError("'resume_match' is required for rewrite coaching.")

            return coach_service.run_rewrite_coach(
                resume_text,
                resume_match,
                bullets,
                target_role,
            )

        return execute(handler)

    @app.post("/api/cover-letter")
    def cover_letter():
        def handler(body):
            updated_cv = required_text_from_keys(body, ["updated_cv"], "Updated CV text")
            job_analysis = optional_json(body, "job_analysis")
            resume_match = optional_json(body, "resume_match")
            return coach_service.run_cover_letter(updated_cv, job_analysis=job_analysis, resume_match=resume_match)

        return execute(handler)

    @app.post("/api/scoring")
    def scoring():
        def handler(body):
            updated_cv = required_text_from_keys(body, ["updated_cv"], "Updated CV text")
            job_analysis = optional_json(body, "job_analysis")
            resume_match = optional_json(body, "resume_match")
            return coach_service.run_scoring_feedback(updated_cv, job_analysis=job_analysis, resume_match=resume_match)

        return execute(handler)

    @app.post("/api/full-analysis")
    def full_analysis():
        def handler(body):
            job_description = require_text(body, "job_description")
            resume_text = required_text_from_keys(body, ["resume_text", "cv_text"], "CV text")
            bullets = optional_string_list(body, "bullets")
            target_role = optional_text(body, "target_role", "data scientist")
            return coach_service.run_full_analysis(job_description, resume_text, bullets, target_role)

        return execute(handler)

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
