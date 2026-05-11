"""Validation grid: minimal but exercises every code path."""

from datetime import UTC, datetime

from pmi_agent.schemas import (
    AwardStructure,
    Confidence,
    PreMarketReport,
    Priority,
    ProvenanceRecord,
    Recommendation,
    RecommendationKind,
    RequirementsProfile,
    ResponseVolumeForecast,
    ScopeFlag,
    ScopeFlagKind,
    Severity,
)
from pmi_agent.validation import (
    CounterfactualAssessment,
    FlagMaterialisation,
    FlagOutcome,
    RecommendationOutcome,
    TenderActuals,
    grid_to_markdown,
    validate_report,
)


def _example_provenance() -> ProvenanceRecord:
    return ProvenanceRecord(
        source_file="example.docx",
        source_file_sha256="0" * 64,
        page_or_paragraph_refs=[],
        extraction_method="test",
        extracted_at=datetime(2026, 5, 11, tzinfo=UTC),
    )


def _example_report() -> PreMarketReport:
    profile = RequirementsProfile(
        title="Example tender",
        contracting_authority="NTA",
        summary="Example",
        award_structure=AwardStructure.RANKED_MULTIPLE,
        provenance=_example_provenance(),
    )
    return PreMarketReport(
        generated_at=datetime(2026, 5, 11, tzinfo=UTC),
        tender=profile,
        response_volume_forecast=ResponseVolumeForecast(
            predicted_submissions_lower=15,
            predicted_submissions_upper=30,
            confidence=Confidence.MEDIUM,
            basis="N=3",
        ),
        scope_flags=[
            ScopeFlag(
                kind=ScopeFlagKind.BUNDLING_RISK,
                description="Bundled scopes",
                evidence_quote="...",
                severity=Severity.HIGH,
            ),
            ScopeFlag(
                kind=ScopeFlagKind.QUALIFICATION_OVERREACH,
                description="Strict rule",
                evidence_quote="...",
                severity=Severity.MEDIUM,
            ),
        ],
        recommendations=[
            Recommendation(
                kind=RecommendationKind.SPLIT_TENDER,
                rationale="Specialist sub-markets",
                priority=Priority.HIGH,
            ),
        ],
        audit_record_ids=["audit-1", "audit-2", "audit-3"],
    )


def _example_actuals(actual_submissions: int = 28) -> TenderActuals:
    return TenderActuals(
        tender_reference="Example RFT",
        contracting_authority="NTA",
        submissions_received=actual_submissions,
        submissions_failed_compliance=7,
        evaluation_duration_months=10,
        flag_outcomes=[
            FlagOutcome(
                kind=ScopeFlagKind.BUNDLING_RISK,
                materialised=FlagMaterialisation.YES,
                notes="Materialised per lessons-learned.",
            ),
            FlagOutcome(
                kind=ScopeFlagKind.QUALIFICATION_OVERREACH,
                materialised=FlagMaterialisation.PARTIAL,
                notes="Partial.",
            ),
            FlagOutcome(
                kind=ScopeFlagKind.SPEC_DRIFT_FROM_MARKET,
                materialised=FlagMaterialisation.YES,
                notes="Materialised — but agent did not flag this.",
            ),
        ],
        recommendation_outcomes=[
            RecommendationOutcome(
                kind=RecommendationKind.SPLIT_TENDER,
                assessment=CounterfactualAssessment.WOULD_HAVE_HELPED,
                notes="Lessons-learned position.",
            ),
        ],
        sources=["samples/Example/everything.docx"],
        curated_by="test",
        curated_at="2026-05-11",
    )


def test_in_range_forecast_is_marked_in_range() -> None:
    grid = validate_report(_example_report(), _example_actuals(actual_submissions=28))
    forecast_row = next(r for r in grid.rows if r.metric == "Response volume")
    assert "in range" in forecast_row.verdict
    assert "upper end" in forecast_row.verdict


def test_out_of_range_forecast_is_marked_out_of_range() -> None:
    grid = validate_report(_example_report(), _example_actuals(actual_submissions=80))
    forecast_row = next(r for r in grid.rows if r.metric == "Response volume")
    assert "out of range" in forecast_row.verdict


def test_scope_flags_classified_by_outcome() -> None:
    grid = validate_report(_example_report(), _example_actuals())
    flag_rows = [r for r in grid.rows if r.section == "scope_flags"]
    by_metric = {r.metric: r for r in flag_rows}
    assert "materialised" in by_metric["bundling_risk"].verdict
    assert "partial" in by_metric["qualification_overreach"].verdict


def test_missed_flag_surfaces_as_false_negative() -> None:
    grid = validate_report(_example_report(), _example_actuals())
    missed = [r for r in grid.rows if r.section == "missed"]
    assert len(missed) == 1
    assert missed[0].metric == "spec_drift_from_market"
    assert "false negative" in missed[0].verdict


def test_grid_renders_to_markdown_table() -> None:
    grid = validate_report(_example_report(), _example_actuals())
    md = grid_to_markdown(grid)
    assert "Pre-Market Intelligence validation" in md
    assert "| Metric |" in md
    assert "bundling_risk" in md
    assert "Summary" in md
