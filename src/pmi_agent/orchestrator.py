"""Deterministic orchestrator: docx in, PreMarketReport out.

Sequencing is fixed (Spec Analyser → Historical Analyst → Recommendation
Agent), not LLM-planned. The orchestrator's job is to thread inputs
and outputs through the agents, record the audit-id chain, and
assemble the final report. Each agent's API surface stays clean and
independently testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pmi_agent.agents.historical_analyst import forecast_volume
from pmi_agent.agents.recommendation import synthesise
from pmi_agent.agents.spec_analyser import analyse_spec
from pmi_agent.audit import AuditLog
from pmi_agent.llm import LLMClient
from pmi_agent.schemas import ComparableTender, PreMarketReport


@dataclass(frozen=True)
class PipelineResult:
    report: PreMarketReport
    audit_record_ids: dict[str, str]


def generate_report(
    docx_path: Path,
    *,
    audit: AuditLog,
    llm: LLMClient | None = None,
    comparables: list[ComparableTender] | None = None,
) -> PipelineResult:
    llm = llm or LLMClient()

    spec_result = analyse_spec(docx_path, audit=audit, llm=llm)
    forecast_result = forecast_volume(
        spec_result.profile,
        audit=audit,
        llm=llm,
        comparables=comparables,
    )
    rec_result = synthesise(
        spec_result.profile,
        forecast_result.forecast,
        audit=audit,
        llm=llm,
    )

    report = PreMarketReport(
        generated_at=datetime.now(UTC),
        tender=spec_result.profile,
        response_volume_forecast=forecast_result.forecast,
        scope_flags=rec_result.scope_flags,
        recommendations=rec_result.recommendations,
        executive_summary=rec_result.executive_summary,
        audit_record_ids=[
            spec_result.audit_record_id,
            forecast_result.audit_record_id,
            rec_result.audit_record_id,
        ],
    )

    return PipelineResult(
        report=report,
        audit_record_ids={
            "spec_analyser": spec_result.audit_record_id,
            "historical_analyst": forecast_result.audit_record_id,
            "recommendation_agent": rec_result.audit_record_id,
        },
    )
