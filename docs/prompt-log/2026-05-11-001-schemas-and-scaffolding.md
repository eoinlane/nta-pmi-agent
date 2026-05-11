# 2026-05-11 — Session 001 — Schemas and scaffolding

## Leading prompt (from Eoin)

> i want to demo something to Declan by the end of the week
> [followed by agreement on the compressed 4-day plan]
> yes start on it now

## What this session produced

- `pyproject.toml` — Python 3.11+ with Pydantic, python-docx, anthropic, streamlit, openpyxl/pandas for samples ingestion, ruff + pytest + pyright in the dev group
- `src/pmi_agent/schemas.py` — the contract every agent reads and writes against:
  - `RequirementsProfile` (Spec Analyser output): title, CPV/NACE codes, value band, qualification barriers, key personnel, unusual requirements, evaluation criteria
  - `ResponseVolumeForecast`, `MarketDepth`, `CostSanityCheck`: agent intermediate outputs, each with explicit `Confidence` band and source citations
  - `ScopeFlag`: issues raised against the draft, with `Severity` and an `evidence_quote`
  - `Recommendation`: constrained to a closed `RecommendationKind` taxonomy of six options; the agent picks and justifies, never invents
  - `PreMarketReport`: the final synthesis
  - `ProvenanceRecord`, `SourceRef`: audit primitives so every claim is defensible in a Tender Approval Form citation
- `tests/test_schemas.py` — smoke tests confirming construction defaults and JSON round-trip

## Two design choices worth flagging

1. **Closed taxonomy on recommendations.** `RecommendationKind` enumerates `SPLIT_TENDER`, `PIN_RFI_FIRST`, `TIGHTEN_QUALIFICATION`, `GEOGRAPHIC_FILTER`, `VALUE_BAND_REVIEW`, `KEY_PERSONNEL_FILTER`. No free-form strings. This is the main guard against hallucinated advice that sounds authoritative.
2. **Ranges, not point estimates.** `predicted_submissions_lower` / `_upper` plus a `Confidence` band on every forecast. Never a single number — Declan and Mark would (rightly) push back on point estimates immediately.

## Verification

```
uv sync          # 100+ deps installed, .venv created
uv run pytest    # 3 passed in 0.09s
uv run ruff      # All checks passed (after auto-fix to StrEnum + UTC idioms)
```

## What's next (session 002)

Spec Analyser v1: load `samples/Drone/RFT*.docx` via `python-docx`, call Claude with a structured-extraction prompt that targets `RequirementsProfile`, validate the output, write to the SQLite audit log.
