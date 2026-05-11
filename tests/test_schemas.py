"""Smoke tests: construction defaults and JSON round-trip of the report."""

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


def _example_provenance() -> ProvenanceRecord:
    return ProvenanceRecord(
        source_file="example.docx",
        source_file_sha256="0" * 64,
        page_or_paragraph_refs=["page 3"],
        extraction_method="python-docx + Claude Opus 4.7",
        extracted_at=datetime(2026, 5, 11, tzinfo=UTC),
    )


def test_requirements_profile_minimal_construction():
    profile = RequirementsProfile(
        title="Test tender",
        contracting_authority="NTA",
        summary="A test tender used in unit tests.",
        provenance=_example_provenance(),
    )
    assert profile.title == "Test tender"
    assert profile.award_structure is AwardStructure.UNKNOWN
    assert profile.key_personnel == []


def test_response_volume_forecast_uses_range_and_confidence():
    forecast = ResponseVolumeForecast(
        predicted_submissions_lower=40,
        predicted_submissions_upper=70,
        confidence=Confidence.MEDIUM,
        basis="Based on 3 comparable awarded contracts on TED in 2023-2025.",
    )
    assert forecast.predicted_submissions_upper == 70
    assert forecast.confidence is Confidence.MEDIUM


def test_pre_market_report_roundtrips_through_json():
    profile = RequirementsProfile(
        title="Drone tender (test fixture)",
        contracting_authority="NTA",
        summary="Drone, timelapse, video production, ISL interpretation.",
        provenance=_example_provenance(),
    )
    report = PreMarketReport(
        generated_at=datetime(2026, 5, 11, tzinfo=UTC),
        tender=profile,
        scope_flags=[
            ScopeFlag(
                kind=ScopeFlagKind.BUNDLING_RISK,
                description="Drone, video production, and ISL bundled in one tender.",
                evidence_quote="Aerial/drone footage ... ISL interpreter support ...",
                severity=Severity.HIGH,
            )
        ],
        recommendations=[
            Recommendation(
                kind=RecommendationKind.SPLIT_TENDER,
                rationale="Drone and studio video production are different specialisms.",
                priority=Priority.HIGH,
            )
        ],
    )

    serialised = report.model_dump_json()
    restored = PreMarketReport.model_validate_json(serialised)

    assert restored.tender.title == "Drone tender (test fixture)"
    assert restored.scope_flags[0].kind is ScopeFlagKind.BUNDLING_RISK
    assert restored.recommendations[0].kind is RecommendationKind.SPLIT_TENDER
