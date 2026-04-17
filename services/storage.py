import os
import sqlite3
import json
from datetime import datetime
from typing import Optional


class Storage:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("COACH_DB_PATH", "coach.db")
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._ensure_tables()

    def _ensure_tables(self):
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                job_description TEXT,
                resume_text TEXT,
                target_role TEXT
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                agent_name TEXT NOT NULL,
                input_text TEXT,
                output_text TEXT,
                output_json TEXT,
                duration_seconds REAL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES runs(id)
            )
            """
        )

        self._conn.commit()

    def create_run(self, job_description: str = "", resume_text: str = "", target_role: str = "") -> int:
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO runs (created_at, job_description, resume_text, target_role) VALUES (?, ?, ?, ?)",
            (datetime.utcnow().isoformat(), job_description, resume_text, target_role),
        )
        self._conn.commit()
        return cur.lastrowid

    def save_agent_call(self, run_id: int, agent_name: str, input_text: str, output_text: str, output_json: dict, duration_seconds: float) -> int:
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO agent_calls (run_id, agent_name, input_text, output_text, output_json, duration_seconds, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                agent_name,
                input_text,
                output_text,
                json.dumps(output_json, ensure_ascii=False) if output_json is not None else None,
                duration_seconds,
                datetime.utcnow().isoformat(),
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass
