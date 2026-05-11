"""The recommendation agent's internal tool-input schema parses round-trip.

We can't easily test the live LLM call without spending money or
mocking the SDK extensively. What we can pin is that the
_RecommendationsBundle shape accepts and round-trips a realistic
payload, so any drift in the schema or the closed taxonomy gets
caught early.
"""

from pmi_agent.agents.recommendation import _RecommendationsBundle
from pmi_agent.schemas import (
    Priority,
    Recommendation,
    RecommendationKind,
    ScopeFlag,
    ScopeFlagKind,
    Severity,
)


def test_recommendations_bundle_roundtrips_with_drone_shaped_payload() -> None:
    bundle = _RecommendationsBundle(
        scope_flags=[
            ScopeFlag(
                kind=ScopeFlagKind.BUNDLING_RISK,
                description="Drone, studio video, and ISL bundled into one tender.",
                evidence_quote=(
                    "Aerial/drone footage of STIIPs ... ISL interpreter "
                    "support ... Irish-language subtitles ..."
                ),
                severity=Severity.HIGH,
            ),
            ScopeFlag(
                kind=ScopeFlagKind.QUALIFICATION_OVERREACH,
                description="Four-formats elimination rule excludes specialists.",
                evidence_quote=(
                    "Four examples of relevant similar experience across "
                    "four media formats. Failure to provide all four "
                    "formats results in elimination."
                ),
                severity=Severity.HIGH,
            ),
        ],
        recommendations=[
            Recommendation(
                kind=RecommendationKind.SPLIT_TENDER,
                rationale=(
                    "Drone/timelapse specialists and studio video houses are "
                    "different specialisms; bundling restricts the qualified pool."
                ),
                evidence_refs=["scope_flag: bundling_risk"],
                priority=Priority.HIGH,
            ),
        ],
        executive_summary=(
            "Bundling drone, studio video, and ISL produces a four-formats "
            "elimination rule that screens out capable specialists; forecast "
            "12-30 submissions, high confidence. Recommend splitting the tender."
        ),
    )

    restored = _RecommendationsBundle.model_validate_json(bundle.model_dump_json())

    assert len(restored.scope_flags) == 2
    assert restored.scope_flags[0].kind is ScopeFlagKind.BUNDLING_RISK
    assert restored.recommendations[0].kind is RecommendationKind.SPLIT_TENDER
    assert "split" in restored.executive_summary.lower()
