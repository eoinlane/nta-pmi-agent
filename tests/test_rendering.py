"""rendering.report_to_markdown produces a useful markdown document."""

from datetime import UTC, datetime

from pmi_agent.rendering import report_to_markdown
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
    validate_report,
)


def _example_report() -> PreMarketReport:
    profile = RequirementsProfile(
        title="Example tender",
        contracting_authority="NTA",
        summary="Example summary.",
        reference="EX-001",
        award_structure=AwardStructure.RANKED_MULTIPLE,
        service_categories=["Service A", "Service B"],
        unusual_requirements=["Specialist requirement"],
        provenance=ProvenanceRecord(
            source_file="example.docx",
            source_file_sha256="0" * 64,
            extraction_method="test",
            extracted_at=datetime(2026, 5, 11, tzinfo=UTC),
        ),
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
            )
        ],
        recommendations=[
            Recommendation(
                kind=RecommendationKind.SPLIT_TENDER,
                rationale="Specialist sub-markets",
                priority=Priority.HIGH,
            )
        ],
        executive_summary="Short summary.",
        audit_record_ids=["audit-1"],
    )


def test_report_renders_with_expected_sections() -> None:
    md = report_to_markdown(_example_report())

    assert "# Pre-Market Intelligence Report" in md
    assert "Example tender" in md
    assert "## Executive summary" in md
    assert "## Response volume forecast" in md
    assert "15-30" in md
    assert "## Scope flags" in md
    assert "bundling_risk" in md
    assert "## Recommendations" in md
    assert "split_tender" in md
    assert "## Tender profile" in md
    assert "Specialist requirement" in md
    assert "## Provenance" in md
    assert "audit-1" in md


def test_report_renders_with_validation_grid_appended() -> None:
    report = _example_report()
    actuals = TenderActuals(
        tender_reference="EX-001",
        contracting_authority="NTA",
        submissions_received=22,
        flag_outcomes=[
            FlagOutcome(
                kind=ScopeFlagKind.BUNDLING_RISK,
                materialised=FlagMaterialisation.YES,
                notes="Materialised.",
            ),
        ],
        recommendation_outcomes=[
            RecommendationOutcome(
                kind=RecommendationKind.SPLIT_TENDER,
                assessment=CounterfactualAssessment.WOULD_HAVE_HELPED,
                notes="Would have helped.",
            ),
        ],
        curated_by="test",
        curated_at="2026-05-11",
    )
    grid = validate_report(report, actuals)
    md = report_to_markdown(report, validation=grid)

    assert "Pre-Market Intelligence validation" in md
    assert "in range" in md
