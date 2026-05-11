"""SQLite-backed audit log.

Every agent call writes one row: which agent, which model, the full
system and user prompts, the structured output, response metadata
(stop_reason, token usage), duration, and any error. This is the
cross-cutting "audit trail" control from the roadmap, made
operational. Reconstructable end-to-end for any tender for the
procurement-law retention period.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_calls (
    id              TEXT    PRIMARY KEY,
    timestamp       TEXT    NOT NULL,
    tender_id       TEXT    NOT NULL,
    agent           TEXT    NOT NULL,
    model           TEXT    NOT NULL,
    system_prompt   TEXT,
    user_prompt     TEXT,
    tool_input_json TEXT,
    response_meta   TEXT,
    duration_ms     INTEGER,
    error           TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_calls_tender    ON agent_calls(tender_id);
CREATE INDEX IF NOT EXISTS idx_agent_calls_timestamp ON agent_calls(timestamp);
"""


class AuditLog:
    """A thin wrapper around a SQLite database."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        path = Path(db_path or os.getenv("AUDIT_DB_PATH", "./audit.db"))
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def record(
        self,
        *,
        tender_id: str,
        agent: str,
        model: str,
        system_prompt: str | None,
        user_prompt: str | None,
        tool_input: dict[str, Any] | None,
        response_meta: dict[str, Any] | None,
        duration_ms: int,
        error: str | None = None,
    ) -> str:
        """Append one row and return its id."""
        row_id = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO agent_calls "
            "(id, timestamp, tender_id, agent, model, system_prompt, user_prompt, "
            " tool_input_json, response_meta, duration_ms, error) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                row_id,
                datetime.now(UTC).isoformat(),
                tender_id,
                agent,
                model,
                system_prompt,
                user_prompt,
                json.dumps(tool_input) if tool_input is not None else None,
                json.dumps(response_meta) if response_meta is not None else None,
                duration_ms,
                error,
            ),
        )
        self.conn.commit()
        return row_id

    def close(self) -> None:
        self.conn.close()


@contextmanager
def open_audit_log(db_path: Path | str | None = None):
    log = AuditLog(db_path)
    try:
        yield log
    finally:
        log.close()
