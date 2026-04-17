from typing import Any, Dict, List, Optional
import json
import time

from services.json_utils import parse_json_response
from services.prompts import (
    COVER_LETTER_PROMPT,
    JOB_ANALYZER_PROMPT,
    RESUME_MATCHER_PROMPT,
    REWRITE_COACH_PROMPT,
    SCORING_FEEDBACK_PROMPT,
    build_agent_input,
)
import os
from services.storage import Storage as SQLiteStorage
from services.file_storage import FileStorage
from services.mock_agent_loader import MockAgentLoader


class JobApplicationCoachService:
    def __init__(self, llm_client, storage: Optional[object] = None):
        self.llm_client = llm_client
        # choose storage backend by env var COACH_STORAGE: 'sqlite' or 'file'
        storage_mode = os.getenv("COACH_STORAGE", "file").strip().lower()
        if storage is not None:
            self.storage = storage
        elif storage_mode == "file":
            self.storage = FileStorage()
        else:
            self.storage = SQLiteStorage()

        # Testing-only mock data loading is intentionally isolated from core runtime logic.
        self.mock_loader = MockAgentLoader.from_env()

    def _ask_model(self, system_prompt: str, user_content: str, expect_json: bool = False):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        raw_output = self.llm_client.chat(messages)
        parsed = None
        if expect_json:
            parsed = parse_json_response(raw_output)
        return raw_output, parsed

    def _call_and_record(self, run_id: int, agent_name: str, system_prompt: str, user_content: str, expect_json: bool = False):
        start = time.time()
        try:
            mock_response = self.mock_loader.load(agent_name, expect_json=expect_json)
            if mock_response is not None:
                raw_output, parsed = mock_response
            else:
                raw_output, parsed = self._ask_model(system_prompt, user_content, expect_json=expect_json)
            duration = time.time() - start

            # Save successful agent call
            try:
                self.storage.save_agent_call(
                    run_id=run_id,
                    agent_name=agent_name,
                    input_text=user_content,
                    output_text=raw_output,
                    output_json=parsed if parsed is not None else {"raw": raw_output},
                    duration_seconds=duration,
                )
            except Exception:
                pass

            return raw_output, parsed
        except Exception as exc:
            # Record the failure details and re-raise
            duration = time.time() - start
            try:
                self.storage.save_agent_call(
                    run_id=run_id,
                    agent_name=agent_name,
                    input_text=user_content,
                    output_text=str(exc),
                    output_json={"error": str(exc)},
                    duration_seconds=duration,
                )
            except Exception:
                pass
            raise

    def _to_json_block(self, payload: Any) -> str:
        if payload is None:
            return "{}"
        if isinstance(payload, str):
            return payload.strip()
        try:
            return json.dumps(payload, indent=2)
        except TypeError:
            return str(payload)

    def _build_resume_matcher_input(
        self,
        resume_text: str,
        job_analysis: Any,
        job_description: str = "",
    ) -> str:
        parts = []
        if job_analysis is not None:
            parts.append(
                "Job Analyzer Output (structured requirements):\n"
                f"{self._to_json_block(job_analysis)}"
            )
        elif job_description.strip():
            parts.append(
                "Job Description:\n"
                f"{job_description.strip()}"
            )
        parts.append("Resume/CV:\n" + resume_text.strip())
        return "\n\n".join(parts)

    def _build_rewrite_coach_input(
        self,
        resume_text: str,
        resume_match: Any,
        bullets: List[str],
        target_role: str,
    ) -> str:
        parts = [
            "Resume Matcher Output:\n" + self._to_json_block(resume_match),
            "Resume/CV:\n" + resume_text.strip(),
        ]

        if bullets:
            bullet_lines = "\n".join(f"- {bullet}" for bullet in bullets)
            parts.append(f"Bullets To Rewrite (prioritize these):\n{bullet_lines}")
        if target_role:
            parts.append(f"Target Role/Industry: {target_role}")

        return "\n\n".join(parts)

    def _build_updated_cv_downstream_input(
        self,
        updated_cv: str,
        job_analysis: Any = None,
        resume_match: Any = None,
    ) -> str:
        parts = ["Updated CV:\n" + (updated_cv or "").strip()]
        if job_analysis is not None:
            parts.append("Job Analyzer Output:\n" + self._to_json_block(job_analysis))
        if resume_match is not None:
            parts.append("Resume Matcher Output:\n" + self._to_json_block(resume_match))
        return "\n\n".join(parts)

    def run_job_analyzer(self, job_description: str, resume_text: str = "", run_id: Optional[int] = None) -> Dict[str, Any]:
        user_content = build_agent_input(job_description, resume_text)
        created_run = False
        if run_id is None:
            run_id = self.storage.create_run(job_description=job_description, resume_text=resume_text)
            created_run = True

        raw, parsed = self._call_and_record(run_id, "job_analyzer", JOB_ANALYZER_PROMPT, user_content, expect_json=True)
        return {"job_analysis": parsed}

    def run_resume_matcher(
        self,
        resume_text: str,
        job_analysis: Any = None,
        job_description: str = "",
        run_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        user_content = self._build_resume_matcher_input(resume_text, job_analysis, job_description)
        if run_id is None:
            run_id = self.storage.create_run(job_description=job_description, resume_text=resume_text)

        raw, parsed = self._call_and_record(run_id, "resume_matcher", RESUME_MATCHER_PROMPT, user_content, expect_json=True)
        return {"resume_match": parsed}

    def run_rewrite_coach(
        self,
        resume_text: str,
        resume_match: Any,
        bullets: List[str],
        target_role: str,
        run_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        user_content = self._build_rewrite_coach_input(resume_text, resume_match, bullets, target_role)
        if run_id is None:
            run_id = self.storage.create_run(job_description="", resume_text=resume_text, target_role=target_role)

        raw, parsed = self._call_and_record(run_id, "rewrite_coach", REWRITE_COACH_PROMPT, user_content, expect_json=False)
        return {"updated_cv": raw}

    def run_cover_letter(
        self,
        updated_cv: str,
        job_analysis: Any = None,
        resume_match: Any = None,
        run_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        user_content = self._build_updated_cv_downstream_input(updated_cv, job_analysis, resume_match)
        if run_id is None:
            run_id = self.storage.create_run(job_description="", resume_text="")

        raw, parsed = self._call_and_record(run_id, "cover_letter", COVER_LETTER_PROMPT, user_content, expect_json=False)
        return {"cover_letter": raw}

    def run_scoring_feedback(
        self,
        updated_cv: str,
        job_analysis: Any = None,
        resume_match: Any = None,
        run_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        user_content = self._build_updated_cv_downstream_input(updated_cv, job_analysis, resume_match)
        if run_id is None:
            run_id = self.storage.create_run(job_description="", resume_text="")

        raw, parsed = self._call_and_record(run_id, "scoring", SCORING_FEEDBACK_PROMPT, user_content, expect_json=True)
        return {"scoring": parsed}

    def run_full_analysis(
        self,
        job_description: str,
        resume_text: str,
        bullets: List[str],
        target_role: str,
    ) -> Dict[str, Any]:
        # create a single run to group all agent calls
        run_id = self.storage.create_run(job_description=job_description, resume_text=resume_text, target_role=target_role)

        analysis = self.run_job_analyzer(job_description, resume_text, run_id=run_id)
        match = self.run_resume_matcher(
            resume_text,
            job_analysis=analysis.get("job_analysis"),
            job_description=job_description,
            run_id=run_id,
        )
        rewrites = self.run_rewrite_coach(
            resume_text,
            match.get("resume_match"),
            bullets,
            target_role,
            run_id=run_id,
        )
        updated_cv = rewrites.get("updated_cv", "")
        cover_letter = self.run_cover_letter(
            updated_cv,
            job_analysis=analysis.get("job_analysis"),
            resume_match=match.get("resume_match"),
            run_id=run_id,
        )
        scoring = self.run_scoring_feedback(
            updated_cv,
            job_analysis=analysis.get("job_analysis"),
            resume_match=match.get("resume_match"),
            run_id=run_id,
        )

        return {
            "run_id": run_id,
            "job_analysis": analysis.get("job_analysis"),
            "resume_match": match.get("resume_match"),
            "updated_cv": updated_cv,
            "cover_letter": cover_letter.get("cover_letter"),
            "scoring": scoring.get("scoring"),
        }

