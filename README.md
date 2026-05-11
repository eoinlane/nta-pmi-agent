# NTA Pre-Market Intelligence Agent

A reference implementation of a Phase 1 Pre-Market Intelligence Agent for tender pre-publication review. Built as a demonstration of agent-assisted development with Claude Code.

Part of a broader roadmap for AI augmentation of the National Transport Authority's procurement lifecycle. The roadmap's hard rule applies throughout: humans make every judgement call; AI structures, retrieves, drafts, and summarises — never scores, ranks, selects, or rejects.

## What it does

Takes a draft tender specification (`.docx`) and produces a Pre-Market Intelligence Report covering:

- Response-volume forecast with explicit range, confidence band, and the comparable awarded contracts the forecast leans on
- Scope flags — bundling risk, qualification overreach, unusual sample requirements, spec drift from market, missing constraints
- Recommendations from a closed taxonomy: `SPLIT_TENDER`, `PIN_RFI_FIRST`, `TIGHTEN_QUALIFICATION`, `GEOGRAPHIC_FILTER`, `VALUE_BAND_REVIEW`, `KEY_PERSONNEL_FILTER`
- An executive summary capped at 120 words, citing the forecast and named flags

Every claim is source-cited and audit-logged so a procurement officer can defend the citation in a Tender Approval Form.

## What it isn't

- Not a production system. Reference build only.
- Not Phases 2-8 of the broader roadmap. Phase 1 only.
- Not a bidder-evaluation tool. Operates on the draft spec, pre-publication. No bidder data.
- Does not train on tender data.

## Architecture

Four agents wired by a deterministic orchestrator (not LLM-planned). See [`docs/architecture.md`](docs/architecture.md) for the full Mermaid diagram.

| # | Agent | Status | Job |
|---|---|---|---|
| 1 | **Spec Analyser** | ✓ built | Parse draft tender → typed `RequirementsProfile` |
| 2 | **Historical Analyst** | ✓ built | Curated TED seed → `ResponseVolumeForecast` with range, confidence, N |
| 3 | **Recommendation Agent** | ✓ built | Synthesise scope flags + closed-taxonomy recommendations + executive summary |
| 4 | **Market Scanner** | deferred | CRO + IAA + curated supplier index → `MarketDepth` |

Plus a **predicted-vs-actual validation grid** — the credibility instrument — that scores any report against curated ground truth for a closed tender.

**Stack:** Python 3.12, Claude API (Opus 4.7), Pydantic for typed contracts, SQLite for the audit log, Streamlit for the UI, `pandoc + prince` for PDF export.

## Quick start

```sh
# 1. Clone, enter the dir, install
git clone https://github.com/eoinlane/nta-pmi-agent
cd nta-pmi-agent
uv sync

# 2. Configure
cp .env.example .env
# edit .env to set ANTHROPIC_API_KEY and (optionally) SAMPLES_DIR

# 3. Enable the confidentiality pre-commit hook
git config core.hooksPath .githooks
```

Five CLI entry points:

```sh
uv run pmi-spec-analyse       path/to/tender.docx          # X-ray of the draft → RequirementsProfile JSON
uv run pmi-historical-analyse path/to/spec.json            # Forecast from comparable awarded contracts
uv run pmi-report             path/to/tender.docx          # Full pipeline → PreMarketReport JSON
uv run pmi-validate           report.json actuals.json     # Score against ground truth
uv run pmi-ui                                              # Launch Streamlit
```

Indicative end-to-end cost: **~70 seconds, ~$1.14** on Opus 4.7 for the full pipeline on a 46-page RFT.

## Validation

Predicted-vs-actual scoring is structural, not optional — every quantitative claim and every scope flag and every recommendation is scored against a `TenderActuals` JSON document curated by hand from the closed tender's procurement pack. The grid surfaces:

- Whether the forecast range captured the actual submission count
- For each predicted scope flag: did it materialise (yes / partial / no / unknown)
- For each recommendation: would it counterfactually have helped
- False negatives: issues that materialised but the agent didn't flag

Sample tender artefacts and ground-truth files are confidential and not included in this repo. Set `SAMPLES_DIR` in `.env` to point at your own.

## Build narrative

This repo is also a case study in agent-assisted development with Claude Code.

- [`docs/build-journal/`](docs/build-journal/) — one short entry per work session; decisions and surprises
- [`docs/prompt-log/`](docs/prompt-log/) — the leading prompt per session; documents human-in-loop at the development layer, mirroring the human-in-loop discipline the agents themselves enforce
- Commit messages favour *why* over *what*

## Confidentiality

Sample data, real tender drafts, generated reports, and the audit database stay out of this repo. The pre-commit hook at [`.githooks/pre-commit`](.githooks/pre-commit) blocks accidental commits of `samples/`, `drafts/`, `reports/`, and known confidential NTA filename patterns. `.gitignore` provides the first layer of defence.

## Status

Active development. The full pipeline is operational end-to-end against the NTA December 2024 drone/timelapse/video RFT as the reference tender, scored against curated ground truth. First demo target: early June 2026 (NTA CTO walkthrough).

## License

Apache 2.0 — see [`LICENSE`](LICENSE).
