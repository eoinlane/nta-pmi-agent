"""Audit log: writes a row, reads it back."""

import sqlite3
from pathlib import Path

from pmi_agent.audit import AuditLog


def test_audit_log_records_and_persists(tmp_path: Path) -> None:
    db = tmp_path / "audit.db"
    audit = AuditLog(db)
    row_id = audit.record(
        tender_id="abc12345",
        agent="spec_analyser",
        model="claude-opus-4-7",
        system_prompt="sys",
        user_prompt="usr",
        tool_input={"title": "Test tender"},
        response_meta={"stop_reason": "tool_use", "usage": {"input_tokens": 100}},
        duration_ms=42,
    )
    assert row_id

    audit.close()

    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT tender_id, agent, model, duration_ms, error FROM agent_calls"
    ).fetchall()
    conn.close()

    assert rows == [("abc12345", "spec_analyser", "claude-opus-4-7", 42, None)]


def test_audit_log_records_errors(tmp_path: Path) -> None:
    db = tmp_path / "audit.db"
    audit = AuditLog(db)
    audit.record(
        tender_id="abc",
        agent="spec_analyser",
        model="claude-opus-4-7",
        system_prompt=None,
        user_prompt=None,
        tool_input=None,
        response_meta=None,
        duration_ms=12,
        error="API timeout",
    )
    audit.close()

    conn = sqlite3.connect(db)
    error = conn.execute("SELECT error FROM agent_calls").fetchone()[0]
    conn.close()
    assert error == "API timeout"
