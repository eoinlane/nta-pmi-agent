"""Core schemas for the NTA Pre-Market Intelligence Agent.

Every agent reads and writes against these types. The Spec Analyser
produces a RequirementsProfile from a draft tender; the Historical
Analyst, Market Scanner, and Recommendation Agent consume that and
contribute to a PreMarketReport. ProvenanceRecord and SourceRef are the
audit primitives that make every claim defensible in a Tender Approval
Form citation.

Two deliberate design choices worth flagging:

1.  Recommendations are constrained to a closed taxonomy. The agent
    selects from RecommendationKind and justifies the choice — it
    cannot invent free-form recommendation strings. This is the main
    guard against hallucinated advice that sounds authoritative.

2.  Quantitative forecasts are ranges with explicit Confidence bands,
    never point estimates. A single predicted-submissions number would
    invite (correctly) immediate pushback from procurement.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# --------------------------------------------------------------------- #
# Provenance and audit primitives                                       #
# --------------------------------------------------------------------- #


class ProvenanceRecord(BaseModel):
    """Where a piece of extracted information came from."""

    model_config = ConfigDict(frozen=True)

    source_file: str
    source_file_sha256: str
    page_or_paragraph_refs: list[str] = Field(default_factory=list)
    extraction_method: str
    extracted_at: datetime


class SourceKind(StrEnum):
    TED = "ted"
    ETENDERS = "etenders"
    CRO = "cro"
    IAA = "iaa"
    INTERNAL_NTA = "internal_nta"
    CURATED_SEED = "curated_seed"
    WEB = "web"


class SourceRef(BaseModel):
    """A pointer to an external source supporting a claim."""

    model_config = ConfigDict(frozen=True)

    kind: SourceKind
    identifier: str
    title: str | None = None
    snippet: str | None = None
    retrieved_at: datetime


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# --------------------------------------------------------------------- #
# Spec Analyser output                                                  #
# --------------------------------------------------------------------- #


class ValueBand(BaseModel):
    lower_eur: float | None = None
    upper_eur: float | None = None
    basis: str


class QualificationKind(StrEnum):
    EXPERIENCE = "experience"
    CERTIFICATION = "certification"
    FINANCIAL = "financial"
    TECHNICAL = "technical"
    GEOGRAPHIC = "geographic"
    PERSONNEL = "personnel"


class QualificationBarrier(BaseModel):
    kind: QualificationKind
    description: str
    threshold: str | None = None


class KeyPersonRequirement(BaseModel):
    role: str
    mandatory: bool = True
    qualifications: list[str] = Field(default_factory=list)


class EvaluationCriterion(BaseModel):
    name: str
    weight_pct: float | None = None
    description: str | None = None


class AwardStructure(StrEnum):
    SINGLE = "single"
    RANKED_MULTIPLE = "ranked_multiple"
    FRAMEWORK = "framework"
    UNKNOWN = "unknown"


class RequirementsProfile(BaseModel):
    """Structured extract of a draft tender — produced by the Spec Analyser."""

    title: str
    reference: str | None = None
    contracting_authority: str
    summary: str
    service_categories: list[str] = Field(default_factory=list)
    cpv_codes: list[str] = Field(default_factory=list)
    nace_codes: list[str] = Field(default_factory=list)
    geographic_scope: str | None = None
    value_band: ValueBand | None = None
    contract_duration_months: int | None = None
    contract_extension_months: int | None = None
    award_structure: AwardStructure = AwardStructure.UNKNOWN
    num_suppliers_sought: int | None = None
    key_personnel: list[KeyPersonRequirement] = Field(default_factory=list)
    qualification_barriers: list[QualificationBarrier] = Field(default_factory=list)
    mandatory_certifications: list[str] = Field(default_factory=list)
    unusual_requirements: list[str] = Field(default_factory=list)
    evaluation_criteria: list[EvaluationCriterion] = Field(default_factory=list)
    submission_format_requirements: list[str] = Field(default_factory=list)
    provenance: ProvenanceRecord


# --------------------------------------------------------------------- #
# Historical Analyst output                                             #
# --------------------------------------------------------------------- #


class ComparableTender(BaseModel):
    source: SourceRef
    title: str
    contracting_authority: str
    cpv_codes: list[str] = Field(default_factory=list)
    value_eur: float | None = None
    awarded_date: datetime | None = None
    response_count: int | None = None
    evaluation_duration_months: int | None = None
    scope_summary: str | None = None


class ResponseVolumeForecast(BaseModel):
    predicted_submissions_lower: int
    predicted_submissions_upper: int
    confidence: Confidence
    basis: str
    comparable_tenders: list[ComparableTender] = Field(default_factory=list)
    evaluation_panel_days_lower: int | None = None
    evaluation_panel_days_upper: int | None = None


# --------------------------------------------------------------------- #
# Market Scanner output                                                 #
# --------------------------------------------------------------------- #


class MarketDepth(BaseModel):
    estimated_suppliers_lower: int
    estimated_suppliers_upper: int
    confidence: Confidence
    basis: str
    sources: list[SourceRef] = Field(default_factory=list)


# --------------------------------------------------------------------- #
# Cost sanity check                                                     #
# --------------------------------------------------------------------- #


class CostSanityCheck(BaseModel):
    nta_estimate_eur: float | None = None
    market_comparator_lower_eur: float | None = None
    market_comparator_upper_eur: float | None = None
    comparable_contracts: list[ComparableTender] = Field(default_factory=list)
    delta_pct: float | None = None
    notes: str | None = None


# --------------------------------------------------------------------- #
# Scope flags                                                           #
# --------------------------------------------------------------------- #


class ScopeFlagKind(StrEnum):
    BUNDLING_RISK = "bundling_risk"
    SPEC_DRIFT_FROM_MARKET = "spec_drift_from_market"
    QUALIFICATION_OVERREACH = "qualification_overreach"
    MISSING_GEOGRAPHIC_CONSTRAINT = "missing_geographic_constraint"
    MISSING_KEY_PERSONNEL_CONSTRAINT = "missing_key_personnel_constraint"
    UNUSUAL_SAMPLE_REQUIREMENT = "unusual_sample_requirement"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ScopeFlag(BaseModel):
    kind: ScopeFlagKind
    description: str
    evidence_quote: str
    severity: Severity
    provenance: ProvenanceRecord | None = None


# --------------------------------------------------------------------- #
# Recommendations — closed taxonomy                                     #
# --------------------------------------------------------------------- #


class RecommendationKind(StrEnum):
    SPLIT_TENDER = "split_tender"
    PIN_RFI_FIRST = "pin_rfi_first"
    TIGHTEN_QUALIFICATION = "tighten_qualification"
    GEOGRAPHIC_FILTER = "geographic_filter"
    VALUE_BAND_REVIEW = "value_band_review"
    KEY_PERSONNEL_FILTER = "key_personnel_filter"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Recommendation(BaseModel):
    kind: RecommendationKind
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)
    priority: Priority


# --------------------------------------------------------------------- #
# The report itself                                                     #
# --------------------------------------------------------------------- #


class PreMarketReport(BaseModel):
    generated_at: datetime
    tender: RequirementsProfile
    market_depth: MarketDepth | None = None
    response_volume_forecast: ResponseVolumeForecast | None = None
    cost_sanity_check: CostSanityCheck | None = None
    scope_flags: list[ScopeFlag] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    executive_summary: str | None = None
    audit_record_ids: list[str] = Field(default_factory=list)
