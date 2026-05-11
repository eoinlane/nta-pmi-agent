# 2026-05-11 — Session 005 — Validation grid: predicted vs actual

## Leading prompt (from Eoin)

> Populate predicted-vs-actual validation grid for drone tender

## What this session produced

- `src/pmi_agent/validation.py` — public framework. Defines `FlagOutcome`, `RecommendationOutcome`, `TenderActuals`, `GridRow`, `ValidationGrid`. The `validate_report(report, actuals)` function computes the grid; `grid_to_markdown(grid)` renders it. No tender-specific references in code.
- `src/pmi_agent/cli/validate.py` — `pmi-validate <report.json> <actuals.json>` entry point.
- `tests/test_validation.py` — 5 tests covering in-range, out-of-range, scope-flag classification, false-negative surfacing, and markdown rendering.
- `reports/ground-truth/drone-tender-actuals.json` — **local-only**, gitignored. Hand-curated ground truth for the drone tender: 28 submissions, 7 compliance fall-out, 10-month evaluation, plus per-flag materialisation and per-recommendation counterfactual assessment with notes and source pointers.

## The headline result

```
$ uv run pmi-validate reports/drone-report.json \
                      reports/ground-truth/drone-tender-actuals.json \
                      -o reports/drone-validation.md
```

**Summary:** `Forecast 15-30 captured the actual (28). 3/4 predicted scope flags materialised. 3/3 recommendations would counterfactually have helped.`

Per-row breakdown:

| Section | Metric | Predicted | Actual | Verdict |
|---|---|---|---|---|
| Quantitative | Response volume | 15-30 | 28 | ✓ in range (upper end) |
| Quantitative | Confidence | medium | — | consistent |
| Quantitative | Compliance fall-out | (implied by flags) | 7 of 28 | ✓ flagged |
| Quantitative | Evaluation duration | 80-180 panel-days | 10 months calendar | — different units |
| Scope flag | bundling_risk | high | yes | ✓ materialised |
| Scope flag | unusual_sample_requirement | high | yes | ✓ materialised |
| Scope flag | qualification_overreach | medium | partial | partial |
| Scope flag | spec_drift_from_market | medium | yes | ✓ materialised |
| Recommendation | SPLIT_TENDER | high | would_have_helped | ✓ |
| Recommendation | TIGHTEN_QUALIFICATION | high | would_have_helped | ✓ |
| Recommendation | PIN_RFI_FIRST | medium | would_have_helped | ✓ |

## The discipline this enforces

The validation grid is the difference between a demo that's *plausible* and a demo that's *defensible*. Three things it makes structural:

1. **Quantitative claims are scored.** The forecast range either captures the actual or it doesn't. No "directionally right" hand-waving.
2. **Scope flags are scored against materialisation.** A flag that didn't materialise isn't a win; a flag the agent missed is a false negative the grid surfaces in its own section.
3. **Recommendations are scored counterfactually.** Curated by humans against the procurement pack — not by the agent assessing its own work.

The honest "partial" verdict on `qualification_overreach` proves the grid is doing real work. A pass-everything validator would not be evidence.

## Confidentiality boundary

The validation *framework* (schemas, comparator, CLI, tests) is open-source in `nta-pmi-agent`. The drone-tender *actuals* (`reports/ground-truth/drone-tender-actuals.json`) and the resulting validation markdown (`reports/drone-validation.md`) are local-only — they reference internal NTA procurement-pack artefacts (Selection Board Report, Assessment Notes, Tender Compliance Sheet) plus quotes from the 20 April 2026 design-thinking session. The code in the public repo is generic; the ground-truth data stays on the machine.

## What's next (session 006)

Streamlit UI — upload a draft tender, see the full pipeline run, view the report and validation grid side-by-side. PDF report export via `pandoc + prince` per Eoin's existing rendering workflow.
