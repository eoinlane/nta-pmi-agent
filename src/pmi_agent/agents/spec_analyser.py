"""Spec Analyser — reads a draft tender, produces a RequirementsProfile.

The agent does one structured-extraction call against Claude. The
RequirementsProfile JSON schema (minus the ``provenance`` field, which
the caller attaches from the file hash) is passed as the tool's
input_schema. The model must return exactly one tool_use block; its
input is then validated through Pydantic.

Hallucination guards:
- Strict schema; unknown fields rejected on validation.
- System prompt explicitly forbids inventing facts not present in the
  document; lists go empty rather than filled with plausible-sounding
  defaults.
- The whole call + result is in the audit log; the audit_record_id is
  returned alongside the profile so a report can cite it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pmi_agent.audit import AuditLog
from pmi_agent.docx_loader import load_docx
from pmi_agent.llm import LLMClient
from pmi_agent.schemas import ProvenanceRecord, RequirementsProfile

SYSTEM_PROMPT = """You are a procurement-tender analyst extracting structured \
requirements from a draft Request for Tender (RFT) or Invitation to Negotiate (ITN).

You read the tender text the user supplies and submit a RequirementsProfile by \
calling the `submit_requirements_profile` tool exactly once.

Rules:
- Only include information present in the document. Never invent or assume.
- Leave optional fields null and list fields empty when the document doesn't \
specify — do not pad with plausible-sounding defaults.
- Quote unusual requirements verbatim where possible.
- value_band: extract any stated estimate, ceiling, or budget figure. If pricing \
is via an appendix schedule with no stated value, set bounds to null and record \
that in `basis`.
- qualification_barriers: list each one separately. kind is one of \
experience / certification / financial / technical / geographic / personnel. \
Put numeric thresholds in `threshold` (e.g. "4 examples", "EUR 1,000,000 turnover").
- award_structure: "single" if one supplier is sought, "ranked_multiple" if a \
ranked list, "framework" if a framework agreement, otherwise "unknown".
- unusual_requirements: anything that atypically narrows the bidder pool — \
foreign-language requirements, accessibility (ISL), unusual sample volumes, \
specialised certifications.
- Do NOT output a `provenance` field — the caller attaches that."""


@dataclass(frozen=True)
class SpecAnalyserResult:
    profile: RequirementsProfile
    audit_record_id: str


def analyse_spec(
    path: Path,
    *,
    audit: AuditLog,
    llm: LLMClient | None = None,
) -> SpecAnalyserResult:
    llm = llm or LLMClient()
    loaded = load_docx(path)
    tender_id = loaded.sha256[:16]

    input_schema = _profile_schema_without_provenance()
    user_prompt = (
        "# Draft tender document\n\n"
        f"Filename: `{path.name}`\n\n"
        "---\n\n"
        f"{loaded.structured_text}\n\n"
        "---\n\n"
        "Extract a RequirementsProfile from the above by calling "
        "`submit_requirements_profile`."
    )

    tool_input, audit_id = llm.extract_structured(
        agent="spec_analyser",
        tender_id=tender_id,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        tool_name="submit_requirements_profile",
        tool_description=(
            "Submit the structured RequirementsProfile extracted from the "
            "draft tender."
        ),
        input_schema=input_schema,
        audit=audit,
    )

    profile_dict = {
        **tool_input,
        "provenance": ProvenanceRecord(
            source_file=path.name,
            source_file_sha256=loaded.sha256,
            page_or_paragraph_refs=[],
            extraction_method=f"python-docx + {llm.model}",
            extracted_at=datetime.now(UTC),
        ).model_dump(mode="json"),
    }
    profile = RequirementsProfile.model_validate(profile_dict)
    return SpecAnalyserResult(profile=profile, audit_record_id=audit_id)


def _profile_schema_without_provenance() -> dict:
    """RequirementsProfile JSON schema with the ``provenance`` field stripped.

    Provenance is attached by the caller from the file hash, so we don't
    ask the model to produce it. Done this way (rather than via a separate
    schema class) so the source of truth stays a single Pydantic model.
    """
    schema = RequirementsProfile.model_json_schema()
    schema = dict(schema)  # shallow copy so we don't mutate the cached one
    if "properties" in schema and "provenance" in schema["properties"]:
        props = dict(schema["properties"])
        del props["provenance"]
        schema["properties"] = props
    if "required" in schema:
        schema["required"] = [f for f in schema["required"] if f != "provenance"]
    return schema
