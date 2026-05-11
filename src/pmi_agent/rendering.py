"""Render a PreMarketReport as a single markdown document.

The markdown is the portable export format — it converts cleanly to
HTML, PDF (via pandoc + prince), or anything else the user wants.
A validation grid, if supplied, is appended after the report.
"""

from __future__ import annotations

from pmi_agent.schemas import PreMarketReport
from pmi_agent.validation import ValidationGrid, grid_to_markdown


def report_to_markdown(
    report: PreMarketReport,
    *,
    validation: ValidationGrid | None = None,
) -> str:
    out: list[str] = []
    out.append("# Pre-Market Intelligence Report")
    out.append("")
    out.append(f"## {report.tender.title}")
    out.append("")
    out.append(f"**Contracting authority:** {report.tender.contracting_authority}  ")
    if report.tender.reference:
        out.append(f"**Reference:** {report.tender.reference}  ")
    out.append(
        f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}"
    )
    out.append("")

    if report.executive_summary:
        out.append("## Executive summary")
        out.append("")
        out.append(report.executive_summary)
        out.append("")

    out.extend(_forecast_section(report))
    out.extend(_scope_flags_section(report))
    out.extend(_recommendations_section(report))
    out.extend(_tender_profile_section(report))

    if validation is not None:
        out.append("---")
        out.append("")
        out.append(grid_to_markdown(validation))
        out.append("")

    out.extend(_provenance_section(report))
    return "\n".join(out)


def _forecast_section(report: PreMarketReport) -> list[str]:
    forecast = report.response_volume_forecast
    if forecast is None:
        return []
    out: list[str] = ["## Response volume forecast", ""]
    out.append(
        f"**Predicted submissions:** {forecast.predicted_submissions_lower}"
        f"-{forecast.predicted_submissions_upper}  "
    )
    out.append(f"**Confidence:** {forecast.confidence.value}  ")
    if forecast.evaluation_panel_days_lower is not None:
        out.append(
            f"**Estimated evaluation effort:** "
            f"{forecast.evaluation_panel_days_lower}-"
            f"{forecast.evaluation_panel_days_upper} panel-days  "
        )
    out.append("")
    out.append("**Basis:**")
    out.append("")
    out.append(forecast.basis)
    out.append("")

    if forecast.comparable_tenders:
        out.append("**Comparable tenders used:**")
        out.append("")
        out.append("| Identifier | Title | Awarded | Responses | Eval (mo) |")
        out.append("|---|---|---|---|---|")
        for comp in forecast.comparable_tenders:
            awarded = comp.awarded_date.strftime("%Y-%m") if comp.awarded_date else "—"
            responses = str(comp.response_count) if comp.response_count else "—"
            eval_dur = (
                str(comp.evaluation_duration_months)
                if comp.evaluation_duration_months
                else "—"
            )
            out.append(
                f"| {comp.source.identifier} | {comp.title} | {awarded} | "
                f"{responses} | {eval_dur} |"
            )
        out.append("")
    return out


def _scope_flags_section(report: PreMarketReport) -> list[str]:
    if not report.scope_flags:
        return []
    out: list[str] = ["## Scope flags", ""]
    for flag in report.scope_flags:
        out.append(f"### {flag.kind.value}  (severity: {flag.severity.value})")
        out.append("")
        out.append(flag.description)
        out.append("")
        out.append(f"> {flag.evidence_quote}")
        out.append("")
    return out


def _recommendations_section(report: PreMarketReport) -> list[str]:
    if not report.recommendations:
        return []
    out: list[str] = ["## Recommendations", ""]
    for rec in report.recommendations:
        out.append(f"### {rec.kind.value}  (priority: {rec.priority.value})")
        out.append("")
        out.append(rec.rationale)
        if rec.evidence_refs:
            out.append("")
            out.append("**Evidence:** " + ", ".join(rec.evidence_refs))
        out.append("")
    return out


def _tender_profile_section(report: PreMarketReport) -> list[str]:
    profile = report.tender
    out: list[str] = ["## Tender profile", ""]
    out.append(f"**Summary:** {profile.summary}")
    out.append("")
    if profile.service_categories:
        out.append("**Service categories:**")
        out.append("")
        for cat in profile.service_categories:
            out.append(f"- {cat}")
        out.append("")
    if profile.qualification_barriers:
        out.append("**Qualification barriers:**")
        out.append("")
        for qb in profile.qualification_barriers:
            threshold = f" ({qb.threshold})" if qb.threshold else ""
            out.append(f"- *{qb.kind.value}*{threshold} — {qb.description}")
        out.append("")
    if profile.unusual_requirements:
        out.append("**Unusual requirements:**")
        out.append("")
        for req in profile.unusual_requirements:
            out.append(f"- {req}")
        out.append("")
    return out


def _provenance_section(report: PreMarketReport) -> list[str]:
    out: list[str] = ["## Provenance", ""]
    out.append(
        f"**Source file:** `{report.tender.provenance.source_file}`  "
    )
    out.append(
        f"**SHA-256:** `{report.tender.provenance.source_file_sha256}`  "
    )
    out.append(
        f"**Extraction method:** {report.tender.provenance.extraction_method}"
    )
    out.append("")
    if report.audit_record_ids:
        out.append("**Agent audit chain:**")
        out.append("")
        for aid in report.audit_record_ids:
            out.append(f"- `{aid}`")
    return out
