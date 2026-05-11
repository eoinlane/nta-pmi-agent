"""Recommendation Agent — synthesises scope flags, closed-taxonomy
recommendations, and an executive summary from upstream agent outputs.

Inputs:
- A RequirementsProfile (Spec Analyser).
- A ResponseVolumeForecast (Historical Analyst).
- Optionally a MarketDepth and CostSanityCheck (Market Scanner and the
  cost agent — both deferred for the demo).

Output:
- A bundle of scope_flags, recommendations, and an executive summary.
  The caller assembles these into the final PreMarketReport.

Two design choices worth stating:

1.  Recommendations are constrained to RecommendationKind — six options
    (SPLIT_TENDER, PIN_RFI_FIRST, TIGHTEN_QUALIFICATION, GEOGRAPHIC_FILTER,
    VALUE_BAND_REVIEW, KEY_PERSONNEL_FILTER). The agent selects from this
    set and justifies; it cannot invent free-form advice.

2.  The prompt asks for *fewer, stronger* recommendations rather than
    filling 6/6 slots. A weak recommendation is worse than no
    recommendation because it dilutes the procurement officer's
    attention.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from pmi_agent.audit import AuditLog
from pmi_agent.llm import LLMClient
from pmi_agent.schemas import (
    CostSanityCheck,
    MarketDepth,
    Recommendation,
    RequirementsProfile,
    ResponseVolumeForecast,
    ScopeFlag,
)


class _RecommendationsBundle(BaseModel):
    """Tool-input shape — the agent's single structured return."""

    scope_flags: list[ScopeFlag] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    executive_summary: str


SYSTEM_PROMPT = """You are a procurement-tender analyst synthesising findings \
from a draft tender's structured requirements profile, a response-volume \
forecast, and (when supplied) market depth and cost sanity-check signals.

Produce three things via the submit_recommendations tool:

1. scope_flags — issues with the draft. Each MUST have:
   - kind drawn from the ScopeFlagKind enum
   - description — what the issue is, in 1-2 sentences
   - evidence_quote — VERBATIM text taken from the profile's \
unusual_requirements list, qualification_barriers descriptions, or summary. \
Do not paraphrase; copy the source string.
   - severity (low / medium / high) reflecting how decisively the evidence \
supports the flag.

2. recommendations — choose ONLY from this closed taxonomy:
     SPLIT_TENDER, PIN_RFI_FIRST, TIGHTEN_QUALIFICATION, \
GEOGRAPHIC_FILTER, VALUE_BAND_REVIEW, KEY_PERSONNEL_FILTER.
   Each MUST have:
   - kind from RecommendationKind
   - rationale — concrete, citing specific scope_flags or forecast numbers
   - evidence_refs — list of short strings pointing to the supporting \
evidence (e.g. "scope_flag: bundling_risk", "forecast: 12-30 submissions").
   - priority (low / medium / high)

3. executive_summary — at most 120 words. Concrete. Cite the predicted \
submission range and named scope_flags. The first sentence should be the \
single most important finding.

Rules of conduct:
- ONLY use the closed taxonomy. Never invent recommendations.
- Better to return 1-2 strong recommendations than 6 weak ones. \
Recommend only what the evidence supports.
- The same flag may justify multiple recommendations — that is fine if \
each adds independent value.
- An evidence_quote that doesn't actually appear in the profile is a \
hallucination. Always copy from the source.
- If no flag of a given kind is warranted, omit it. Do not pad."""


@dataclass(frozen=True)
class RecommendationResult:
    scope_flags: list[ScopeFlag]
    recommendations: list[Recommendation]
    executive_summary: str
    audit_record_id: str


def synthesise(
    profile: RequirementsProfile,
    forecast: ResponseVolumeForecast,
    *,
    audit: AuditLog,
    llm: LLMClient | None = None,
    market_depth: MarketDepth | None = None,
    cost_check: CostSanityCheck | None = None,
) -> RecommendationResult:
    llm = llm or LLMClient()

    tender_id = profile.provenance.source_file_sha256[:16]
    user_prompt = _build_prompt(profile, forecast, market_depth, cost_check)
    input_schema = _RecommendationsBundle.model_json_schema()

    tool_input, audit_id = llm.extract_structured(
        agent="recommendation_agent",
        tender_id=tender_id,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        tool_name="submit_recommendations",
        tool_description=(
            "Submit scope flags, closed-taxonomy recommendations, and an "
            "executive summary for the draft tender."
        ),
        input_schema=input_schema,
        audit=audit,
    )

    bundle = _RecommendationsBundle.model_validate(tool_input)
    return RecommendationResult(
        scope_flags=bundle.scope_flags,
        recommendations=bundle.recommendations,
        executive_summary=bundle.executive_summary,
        audit_record_id=audit_id,
    )


def _build_prompt(
    profile: RequirementsProfile,
    forecast: ResponseVolumeForecast,
    market_depth: MarketDepth | None,
    cost_check: CostSanityCheck | None,
) -> str:
    parts: list[str] = []
    parts.append("# Draft tender — RequirementsProfile")
    parts.append(
        f"```json\n{profile.model_dump_json(indent=2, exclude={'provenance'})}\n```"
    )
    parts.append("# Response-volume forecast")
    parts.append(f"```json\n{forecast.model_dump_json(indent=2)}\n```")

    if market_depth is not None:
        parts.append("# Market depth")
        parts.append(f"```json\n{market_depth.model_dump_json(indent=2)}\n```")
    else:
        parts.append(
            "# Market depth: not supplied (Market Scanner deferred for this run)."
        )

    if cost_check is not None:
        parts.append("# Cost sanity check")
        parts.append(f"```json\n{cost_check.model_dump_json(indent=2)}\n```")

    parts.append(
        "Synthesise scope_flags, recommendations (closed taxonomy), and an "
        "executive summary by calling submit_recommendations."
    )
    return "\n\n".join(parts)
