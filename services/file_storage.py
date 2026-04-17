import os
import json
from datetime import datetime
from typing import Optional


class FileStorage:
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = base_path or os.getenv("COACH_FILE_STORAGE_PATH", ".")
        os.makedirs(self.base_path, exist_ok=True)

    def _safe_run_id(self, run_id: str) -> str:
        return str(run_id).replace(":", "-").replace(".", "-")

    def create_run(self, job_description: str = "", resume_text: str = "", target_role: str = "") -> str:
        run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%S%f")
        safe_run_id = self._safe_run_id(run_id)
        meta = {
            "run_id": run_id,
            "created_at": datetime.utcnow().isoformat(),
            "job_description": job_description,
            "resume_text": resume_text,
            "target_role": target_role,
        }
        filename = f"run_{safe_run_id}.json"
        with open(os.path.join(self.base_path, filename), "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=2)
        return run_id

    def save_agent_call(self, run_id: str, agent_name: str, input_text: str, output_text: str, output_json: dict, duration_seconds: float) -> int:
        safe_run_id = self._safe_run_id(run_id)
        # Sequence only for this run+agent in root directory.
        prefix = f"agent_{safe_run_id}_{agent_name}_"
        existing = [n for n in os.listdir(self.base_path) if n.startswith(prefix) and n.endswith(".json")]
        seq = len(existing) + 1
        filename = f"{prefix}{seq:03d}.json"
        payload = {
            "run_id": run_id,
            "created_at": datetime.utcnow().isoformat(),
            "agent_name": agent_name,
            "input_text": input_text,
            "output_text": output_text,
            "output_json": output_json,
            "duration_seconds": duration_seconds,
        }
        with open(os.path.join(self.base_path, filename), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        return seq

    def close(self):
        return
