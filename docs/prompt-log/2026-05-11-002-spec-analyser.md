# 2026-05-11 — Session 002 — Spec Analyser end-to-end

## Leading prompt (from Eoin)

> yes
> [in response to: "draft the .env so you can paste the key in, then push on with the Spec Analyser"]

## What this session produced

Four cooperating modules and the agent that composes them:

- `src/pmi_agent/docx_loader.py` — walks the `.docx` body in document order, renders headings as `#`-style markdown, tables as pipe-delimited rows. Returns text + SHA-256 + path.
- `src/pmi_agent/audit.py` — SQLite `agent_calls` table with one row per agent invocation: full prompts, structured output, response metadata, duration, error.
- `src/pmi_agent/llm.py` — Anthropic SDK wrapper. `extract_structured()` forces a single tool call whose `input_schema` is the Pydantic-derived JSON schema; logs to audit before returning.
- `src/pmi_agent/agents/spec_analyser.py` — strips `provenance` from the schema (caller attaches it from the file hash, the model never invents provenance), runs one extraction call, re-validates the result through Pydantic.
- `src/pmi_agent/cli/spec_analyse.py` — `pmi-spec-analyse <path>` entry point with `SAMPLES_DIR`-aware path resolution.

## Hallucination guards in the prompt

System prompt explicitly forbids inventing facts not in the document; optional fields stay null and lists stay empty rather than padded with plausible defaults. The agent obeyed: `cpv_codes` and `nace_codes` are empty (the drone RFT doesn't quote them), `value_band.lower_eur`/`upper_eur` are null with a `basis` field that explains *why* (rate-card with notional volumes, no stated value).

## First end-to-end run — drone RFT

```
$ uv run pmi-spec-analyse "Drone/RFT - Provision of Drone Timelapse and Video Production Services 30.12.2024.docx" -o reports/drone-spec.json

Analysing: ...samples/Drone/RFT...30.12.2024.docx
Audit record: be1e9e82-428a-436d-8024-652bf81ec478
Wrote reports/drone-spec.json
```

| Metric | Value |
|---|---|
| Model | claude-opus-4-7 |
| Duration | 27.5 s |
| Input tokens | 26,762 |
| Output tokens | 2,862 |
| Stop reason | tool_use |
| Approx. cost | ~$0.62 |

## What the agent extracted

- 7 distinct service categories (drone, timelapse, vox-pop video, photography, editing, subtitling, ISL)
- `award_structure: ranked_multiple`, `num_suppliers_sought: 2` — exactly correct
- 3 mandatory key personnel (Lead Videographer, Lead Photographer, Account Manager)
- 7 qualification barriers — including the "4 examples covering all 4 media formats" elimination rule, Article 57, Russian-sanctions compliance
- 10 unusual requirements — bundling-and-overreach signals the Recommendation Agent will use
- 3 evaluation criteria with weights (30/30/40)
- 13 submission-format constraints with concrete numbers
- Provenance with file SHA-256 and extraction method

## Why this matters for the demo

This is the foundation. Every downstream agent reads from a `RequirementsProfile`, and the quality of the report is bounded by the quality of this extraction. The unusual_requirements list alone gives the Recommendation Agent rich evidence for `SPLIT_TENDER` (drone + studio video + ISL bundled) and `TIGHTEN_QUALIFICATION` (the 4-format rule arguably eliminates capable specialist vendors).

## What's next (session 003)

Hand-curate `src/pmi_agent/data/historical_seed.json` — 5-10 comparable awarded contracts from TED matching drone/video/timelapse/media-production scope. Build the Historical Analyst against that seed; produce a `ResponseVolumeForecast` with explicit N= and confidence band.
