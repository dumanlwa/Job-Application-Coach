import json
import os
from pathlib import Path
from typing import Any, Optional, Tuple

from services.json_utils import parse_json_response


class MockAgentLoader:
    """Loads deterministic agent outputs from disk for mock/test runs."""

    def __init__(self, run_id: str = "", data_dir: str = "."):
        self.run_id = (run_id or "").strip()
        self.data_dir = (data_dir or ".").strip()

    @classmethod
    def from_env(cls) -> "MockAgentLoader":
        return cls(
            run_id=os.getenv("COACH_MOCK_RUN_ID", ""),
            data_dir=os.getenv("COACH_MOCK_DATA_DIR", "."),
        )

    def is_enabled(self) -> bool:
        return bool(self.run_id)

    def load(self, agent_name: str, expect_json: bool = False) -> Optional[Tuple[str, Any]]:
        if not self.is_enabled():
            return None

        filename = f"agent_{self.run_id}_{agent_name}_001.json"
        file_path = Path(self.data_dir) / filename
        if not file_path.exists():
            raise RuntimeError(f"Mock file not found for agent '{agent_name}': {file_path}")

        with open(file_path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)

        raw_output = payload.get("output_text", "")
        parsed = parse_json_response(raw_output) if expect_json else None
        return raw_output, parsed
