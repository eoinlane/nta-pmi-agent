# NTA Pre-Market Intelligence Agent

A reference implementation of a Phase 1 Pre-Market Intelligence Agent for tender pre-publication review. Built as a demonstration of agent-assisted development with Claude Code.

Part of a broader roadmap for AI augmentation of the National Transport Authority's procurement lifecycle. The roadmap's hard rule applies throughout: humans make every judgement call; AI structures, retrieves, drafts, and summarises — never scores, ranks, selects, or rejects.

## What it does

Takes a draft tender specification and produces a Pre-Market Intelligence Report covering:

- Estimated market depth (qualified suppliers in scope)
- Response-volume forecast with confidence band
- Scope flags — spec drift, unusual bundling, qualification barriers
- Cost-estimate sanity check against comparable awarded contracts
- Recommendations from a closed taxonomy: split, PIN/RFI first, tighten qualification, geographic filter, value-band review, key-personnel filter

Every claim is source-cited so a procurement officer can defend the citation in a Tender Approval Form.

## What it isn't

- Not a production system. Reference build only.
- Not Phases 2-8 of the roadmap. Phase 1 only.
- Not a bidder-evaluation tool. Operates on the draft spec, pre-publication. No bidder data.
- Does not train on tender data.

## Architecture

Four agents wired by a deterministic orchestrator (not LLM-planned):

1. **Spec Analyser** — parses draft tender, extracts a structured `RequirementsProfile`
2. **Historical Analyst** — TED API + curated archive for comparable awarded contracts; produces response-volume forecast with explicit N=
3. **Market Scanner** — CRO snapshot + IAA register + curated supplier index
4. **Recommendation Agent** — closed-taxonomy synthesis with source citation

Stack: Python, Claude API, SQLite for audit log and historical cache, Streamlit for the demo UI, `pandoc` + `prince` for PDF report export. Stack details confirmed as the build progresses.

## Validation

The agent's credibility comes from a **predicted-vs-actual grid** run retrospectively on a closed tender with a known outcome. The reference test case is NTA's December 2024 drone/timelapse/video RFT (28 submissions, 7-8 lost at compliance, 10-month evaluation, awarded values known).

Sample tender artefacts are confidential and not included in this repo. Set `SAMPLES_DIR` in `.env` to point at your own.

## Build narrative

This repo is also a case study in agent-assisted development with Claude Code.

- `docs/build-journal/` — one short entry per work session, captures decisions and surprises
- `docs/prompt-log/` — leading prompt per session; documents human-in-loop at the development layer, mirroring the human-in-loop discipline the agents themselves enforce
- Commit messages favour the *why* over the *what*

## Confidentiality

Sample data and any reports containing real tender content stay out of this repo. A pre-commit hook at `.githooks/pre-commit` blocks accidental commits of `samples/`, `drafts/`, or known confidential filenames.

Enable the hook once after cloning:

```sh
git config core.hooksPath .githooks
```

## Status

Active development. First demo target: early June 2026 (NTA CTO walkthrough).

## License

Apache 2.0 — see `LICENSE`.
