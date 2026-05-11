"""Historical Analyst — produces a ResponseVolumeForecast from comparables.

Inputs:
- A RequirementsProfile from the Spec Analyser.
- A list of ComparableTender objects. By default the hand-curated seed
  is used; the production caller swaps in a live TED query.

Output:
- A ResponseVolumeForecast with explicit lower/upper bounds, a Confidence
  band justified by the number of close matches, and the subset of
  comparables the model actually relied on.

Hallucination guards:
- The system prompt explicitly forbids inventing comparables or
  extrapolating beyond what the supplied set supports.
- The schema is forced via tool use; comparable_tenders in the output
  must be drawn from the input set, not invented.
- Confidence is tied to the number of close matches (≥4 close → high,
  2-3 → medium, ≤1 → low) so the agent cannot claim high confidence
  from thin evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from pmi_agent.audit import AuditLog
from pmi_agent.data.seed_loader import load_comparables
from pmi_agent.llm import LLMClient
from pmi_agent.schemas import (
    ComparableTender,
    RequirementsProfile,
    ResponseVolumeForecast,
)

SYSTEM_PROMPT = """You are a procurement-tender analyst forecasting how many \
submissions a draft tender will receive, and how long evaluation will take, \
based on a supplied set of comparable awarded contracts.

Rules:
- ONLY use the comparable contracts the user provides. Do not invent new ones \
or extrapolate from outside this set.
- Identify the subset of comparables that genuinely match the draft tender's \
scope and shape — similar service mix, similar bundling, similar award \
structure, similar geographic scope.
- Use that subset to produce a response-volume range and an evaluation-effort \
estimate (panel-days). State N (the number of close matches) explicitly in \
`basis`.
- Confidence levels:
    high   — ≥4 comparables match closely
    medium — 2 or 3 close matches
    low    — 1 close match or only weak matches
- Ranges must be wide enough to be honest. A "30-35" range against thin \
evidence is a point estimate in disguise — prefer "20-45" with `low` \
confidence over false precision.
- Reflect bundling realities: bundled scopes draw more responses but \
evaluation takes longer; specialist scopes draw fewer responses but are \
quicker.
- In `comparable_tenders`, return only the comparables you actually relied \
on, copied verbatim from the input.
- Return your answer by calling the `submit_response_volume_forecast` tool."""


@dataclass(frozen=True)
class HistoricalAnalystResult:
    forecast: ResponseVolumeForecast
    audit_record_id: str
    comparables_considered: int


def forecast_volume(
    profile: RequirementsProfile,
    *,
    audit: AuditLog,
    llm: LLMClient | None = None,
    comparables: list[ComparableTender] | None = None,
) -> HistoricalAnalystResult:
    llm = llm or LLMClient()
    if comparables is None:
        comparables = load_comparables(datetime.now(UTC))

    tender_id = profile.provenance.source_file_sha256[:16]
    user_prompt = _build_prompt(profile, comparables)
    input_schema = ResponseVolumeForecast.model_json_schema()

    tool_input, audit_id = llm.extract_structured(
        agent="historical_analyst",
        tender_id=tender_id,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        tool_name="submit_response_volume_forecast",
        tool_description="Submit the response-volume forecast for the draft tender.",
        input_schema=input_schema,
        audit=audit,
    )

    forecast = ResponseVolumeForecast.model_validate(tool_input)
    return HistoricalAnalystResult(
        forecast=forecast,
        audit_record_id=audit_id,
        comparables_considered=len(comparables),
    )


def _build_prompt(
    profile: RequirementsProfile,
    comparables: list[ComparableTender],
) -> str:
    profile_payload = profile.model_dump_json(indent=2, exclude={"provenance"})
    comparables_payload = "\n\n".join(
        f"## Comparable {i + 1}\n```json\n{c.model_dump_json(indent=2)}\n```"
        for i, c in enumerate(comparables)
    )
    return (
        "# Draft tender profile\n\n"
        f"```json\n{profile_payload}\n```\n\n"
        f"# Comparable awarded contracts (N={len(comparables)})\n\n"
        f"{comparables_payload}\n\n"
        "Identify which comparables genuinely match this draft's scope and "
        "shape, then submit a ResponseVolumeForecast by calling "
        "`submit_response_volume_forecast`."
    )
