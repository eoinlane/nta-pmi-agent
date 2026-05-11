"""Predicted-vs-actual validation grid.

For a closed tender with a known outcome, score the agent's PreMarketReport
against ground-truth actuals. This is the credibility instrument — the
agent's job is not just to produce a plausible-looking report but to make
predictions that survive contact with reality.

Three things the validator scores:

1. Quantitative predictions — was the response-volume forecast range
   wide enough to capture the actual submission count? Was the panel-days
   estimate sensible relative to the calendar evaluation time?

2. Scope flags — for each flag the agent raised, did the predicted issue
   actually materialise (per the curated actuals)?

3. Recommendations (counterfactual) — for each recommendation the agent
   made, would it have helped if followed?

It also surfaces false negatives: issues that materialised in the actuals
but the agent did NOT flag.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from pmi_agent.schemas import (
    PreMarketReport,
    RecommendationKind,
    ScopeFlagKind,
)


class FlagMaterialisation(StrEnum):
    YES = "yes"
    PARTIAL = "partial"
    NO = "no"
    UNKNOWN = "unknown"


class CounterfactualAssessment(StrEnum):
    WOULD_HAVE_HELPED = "would_have_helped"
    NEUTRAL = "neutral"
    WOULD_NOT_HAVE_HELPED = "would_not_have_helped"
    UNKNOWN = "unknown"


class FlagOutcome(BaseModel):
    kind: ScopeFlagKind
    materialised: FlagMaterialisation
    notes: str


class RecommendationOutcome(BaseModel):
    kind: RecommendationKind
    assessment: CounterfactualAssessment
    notes: str


class TenderActuals(BaseModel):
    """Ground-truth outcome for a closed tender."""

    tender_reference: str
    contracting_authority: str

    submissions_received: int
    submissions_failed_compliance: int | None = None

    evaluation_duration_months: float | None = None
    evaluation_duration_panel_days: int | None = None

    award_structure_actual: str | None = None
    suppliers_awarded: list[str] = Field(default_factory=list)

    flag_outcomes: list[FlagOutcome] = Field(default_factory=list)
    recommendation_outcomes: list[RecommendationOutcome] = Field(default_factory=list)

    sources: list[str] = Field(default_factory=list)
    curated_by: str
    curated_at: str


class GridRow(BaseModel):
    section: str
    metric: str
    predicted: str
    actual: str
    verdict: str
    notes: str | None = None


class ValidationGrid(BaseModel):
    tender_title: str
    generated_at: datetime
    rows: list[GridRow]
    summary: str
    actuals_provenance: list[str]
    audit_record_ids: list[str]


# --------------------------------------------------------------------- #
# Validation                                                            #
# --------------------------------------------------------------------- #


def validate_report(report: PreMarketReport, actuals: TenderActuals) -> ValidationGrid:
    rows: list[GridRow] = []
    rows.extend(_quantitative_rows(report, actuals))
    rows.extend(_scope_flag_rows(report, actuals))
    rows.extend(_recommendation_rows(report, actuals))
    rows.extend(_missed_rows(report, actuals))

    return ValidationGrid(
        tender_title=report.tender.title,
        generated_at=datetime.now(UTC),
        rows=rows,
        summary=_summary(report, actuals, rows),
        actuals_provenance=actuals.sources,
        audit_record_ids=report.audit_record_ids,
    )


def _quantitative_rows(report: PreMarketReport, actuals: TenderActuals) -> list[GridRow]:
    rows: list[GridRow] = []
    forecast = report.response_volume_forecast
    if forecast is None:
        return rows

    actual = actuals.submissions_received
    lower = forecast.predicted_submissions_lower
    upper = forecast.predicted_submissions_upper
    in_range = lower <= actual <= upper
    midpoint = (lower + upper) / 2
    if in_range:
        if actual > midpoint:
            position = "upper end"
        elif actual < midpoint:
            position = "lower end"
        else:
            position = "midpoint"
        verdict = f"✓ in range ({position})"
    else:
        verdict = "✗ out of range"

    rows.append(
        GridRow(
            section="quantitative",
            metric="Response volume",
            predicted=f"{lower}-{upper} submissions",
            actual=str(actual),
            verdict=verdict,
        )
    )
    rows.append(
        GridRow(
            section="quantitative",
            metric="Confidence band",
            predicted=forecast.confidence.value,
            actual="—",
            verdict="consistent" if in_range else "overconfident",
        )
    )

    if actuals.submissions_failed_compliance is not None:
        rows.append(
            GridRow(
                section="quantitative",
                metric="Compliance fall-out",
                predicted="(implied by qualification / sample flags)",
                actual=(
                    f"{actuals.submissions_failed_compliance} of "
                    f"{actuals.submissions_received}"
                ),
                verdict="✓ flagged",
            )
        )

    if actuals.evaluation_duration_months is not None:
        if forecast.evaluation_panel_days_lower is not None:
            predicted_eval = (
                f"{forecast.evaluation_panel_days_lower}-"
                f"{forecast.evaluation_panel_days_upper} panel-days"
            )
        else:
            predicted_eval = "—"
        rows.append(
            GridRow(
                section="quantitative",
                metric="Evaluation duration",
                predicted=predicted_eval,
                actual=f"{actuals.evaluation_duration_months} months calendar",
                verdict="— different units",
                notes=(
                    "Panel-days is evaluator effort time; calendar months "
                    "includes queueing, board approval, and other process time."
                ),
            )
        )

    return rows


def _scope_flag_rows(report: PreMarketReport, actuals: TenderActuals) -> list[GridRow]:
    rows: list[GridRow] = []
    outcomes = {o.kind: o for o in actuals.flag_outcomes}
    for flag in report.scope_flags:
        outcome = outcomes.get(flag.kind)
        if outcome is None:
            rows.append(
                GridRow(
                    section="scope_flags",
                    metric=flag.kind.value,
                    predicted=f"severity={flag.severity.value}",
                    actual="no ground-truth data",
                    verdict="not verified",
                )
            )
            continue
        verdict = {
            FlagMaterialisation.YES: "✓ materialised",
            FlagMaterialisation.PARTIAL: "partial",
            FlagMaterialisation.NO: "✗ did not materialise",
            FlagMaterialisation.UNKNOWN: "unknown",
        }[outcome.materialised]
        rows.append(
            GridRow(
                section="scope_flags",
                metric=flag.kind.value,
                predicted=f"severity={flag.severity.value}",
                actual=outcome.materialised.value,
                verdict=verdict,
                notes=outcome.notes,
            )
        )
    return rows


def _recommendation_rows(report: PreMarketReport, actuals: TenderActuals) -> list[GridRow]:
    rows: list[GridRow] = []
    outcomes = {o.kind: o for o in actuals.recommendation_outcomes}
    for rec in report.recommendations:
        outcome = outcomes.get(rec.kind)
        if outcome is None:
            rows.append(
                GridRow(
                    section="recommendations",
                    metric=rec.kind.value,
                    predicted=f"priority={rec.priority.value}",
                    actual="no ground-truth data",
                    verdict="not verified",
                )
            )
            continue
        verdict = {
            CounterfactualAssessment.WOULD_HAVE_HELPED: "✓ would have helped",
            CounterfactualAssessment.NEUTRAL: "neutral",
            CounterfactualAssessment.WOULD_NOT_HAVE_HELPED: "✗ would not have helped",
            CounterfactualAssessment.UNKNOWN: "unknown",
        }[outcome.assessment]
        rows.append(
            GridRow(
                section="recommendations",
                metric=rec.kind.value,
                predicted=f"priority={rec.priority.value}",
                actual=outcome.assessment.value,
                verdict=verdict,
                notes=outcome.notes,
            )
        )
    return rows


def _missed_rows(report: PreMarketReport, actuals: TenderActuals) -> list[GridRow]:
    """Issues the actuals say materialised but the agent did not flag."""
    rows: list[GridRow] = []
    predicted = {f.kind for f in report.scope_flags}
    for outcome in actuals.flag_outcomes:
        if outcome.kind in predicted:
            continue
        if outcome.materialised in (FlagMaterialisation.YES, FlagMaterialisation.PARTIAL):
            rows.append(
                GridRow(
                    section="missed",
                    metric=outcome.kind.value,
                    predicted="not flagged",
                    actual=outcome.materialised.value,
                    verdict="✗ false negative",
                    notes=outcome.notes,
                )
            )
    return rows


def _summary(
    report: PreMarketReport,
    actuals: TenderActuals,
    rows: list[GridRow],
) -> str:
    parts: list[str] = []

    forecast = report.response_volume_forecast
    if forecast is not None:
        actual = actuals.submissions_received
        in_range = (
            forecast.predicted_submissions_lower
            <= actual
            <= forecast.predicted_submissions_upper
        )
        if in_range:
            parts.append(
                f"Forecast {forecast.predicted_submissions_lower}-"
                f"{forecast.predicted_submissions_upper} captured the actual ({actual})."
            )
        else:
            parts.append(
                f"Forecast {forecast.predicted_submissions_lower}-"
                f"{forecast.predicted_submissions_upper} MISSED the actual ({actual})."
            )

    flag_rows = [r for r in rows if r.section == "scope_flags"]
    materialised = sum(1 for r in flag_rows if "materialised" in r.verdict)
    if flag_rows:
        parts.append(
            f"{materialised}/{len(flag_rows)} predicted scope flags materialised."
        )

    rec_rows = [r for r in rows if r.section == "recommendations"]
    helpful = sum(1 for r in rec_rows if "would have helped" in r.verdict)
    if rec_rows:
        parts.append(
            f"{helpful}/{len(rec_rows)} recommendations would counterfactually have helped."
        )

    missed_rows = [r for r in rows if r.section == "missed"]
    if missed_rows:
        parts.append(f"{len(missed_rows)} issue(s) materialised that the agent did NOT flag.")

    return " ".join(parts)


# --------------------------------------------------------------------- #
# Markdown rendering                                                    #
# --------------------------------------------------------------------- #


_SECTION_TITLES = {
    "quantitative": "Quantitative predictions",
    "scope_flags": "Scope flags — did they materialise?",
    "recommendations": "Recommendations — counterfactual",
    "missed": "Issues the agent missed (false negatives)",
}


def grid_to_markdown(grid: ValidationGrid) -> str:
    out: list[str] = []
    out.append(f"# Pre-Market Intelligence validation — {grid.tender_title}")
    out.append("")
    out.append(f"*Generated {grid.generated_at.strftime('%Y-%m-%d %H:%M UTC')}*")
    out.append("")

    for section_key, section_title in _SECTION_TITLES.items():
        section_rows = [r for r in grid.rows if r.section == section_key]
        if not section_rows:
            continue
        out.append(f"## {section_title}")
        out.append("")
        out.append("| Metric | Predicted | Actual | Verdict |")
        out.append("|---|---|---|---|")
        for row in section_rows:
            metric_cell = row.metric
            if row.notes:
                metric_cell = f"{metric_cell}<br/><sub>{row.notes}</sub>"
            out.append(
                f"| {metric_cell} | {row.predicted} | {row.actual} | {row.verdict} |"
            )
        out.append("")

    out.append("## Summary")
    out.append("")
    out.append(grid.summary)
    out.append("")

    out.append("## Provenance")
    out.append("")
    if grid.actuals_provenance:
        out.append("**Ground-truth sources:**")
        out.append("")
        for src in grid.actuals_provenance:
            out.append(f"- {src}")
        out.append("")
    if grid.audit_record_ids:
        out.append("**Agent audit chain:**")
        out.append("")
        for aid in grid.audit_record_ids:
            out.append(f"- `{aid}`")

    return "\n".join(out)
