# 2026-05-11 — Session 004 — Recommendation Agent and the orchestrator

## Leading prompt (from Eoin)

> build the recommendation agent

## What this session produced

- `src/pmi_agent/agents/recommendation.py` — the third agent. Takes a `RequirementsProfile` and a `ResponseVolumeForecast`, returns scope flags, closed-taxonomy recommendations, and an executive summary in a single Claude call.
- `src/pmi_agent/orchestrator.py` — deterministic pipeline: Spec Analyser → Historical Analyst → Recommendation Agent. Threads inputs through, captures the audit-id chain, assembles the final `PreMarketReport`.
- `src/pmi_agent/cli/report.py` — `pmi-report <docx>` entry point. Writes the full report JSON, prints an executive summary + scope flags + recommendations + audit chain to stderr.
- `tests/test_recommendation_bundle.py` — schema round-trip test for the agent's internal tool-input shape, so closed-taxonomy or schema drift gets caught early without spending API tokens.

## Hallucination guards in the prompt

- Recommendations may only be drawn from the closed `RecommendationKind` enum (six options).
- `evidence_quote` on every scope flag must be verbatim text from the profile — `unusual_requirements`, `qualification_barriers`, or `summary`. Paraphrase is forbidden.
- "Better to return 1-2 strong recommendations than 6 weak ones" is explicit in the system prompt — recommendations must be earned, not padded.
- Executive summary capped at 120 words, must cite the forecast range and named scope flags.

## First end-to-end pipeline run — drone tender

```
$ uv run pmi-report "Drone/RFT - Provision of Drone Timelapse and Video Production Services 30.12.2024.docx" -o reports/drone-report.json
```

| Agent | Duration | Input tok | Output tok |
|---|---|---|---|
| Spec Analyser | 30.9 s | 26,762 | 3,011 |
| Historical Analyst | 17.4 s | 7,687 | 1,718 |
| Recommendation Agent | 22.9 s | 7,532 | 2,028 |
| **Pipeline total** | **71.2 s** | **41,981** | **6,757** |

Approx end-to-end cost on Opus 4.7: **~$1.14 per draft tender**.

## What the Recommendation Agent produced

**Forecast (this run):** 15-30 submissions, **medium** confidence — note that on the earlier standalone run the Historical Analyst returned 12-30 / high. The fresh pipeline run self-corrected toward `medium` once it had to defend the claim alongside the recommendation synthesis. Useful exhibit: the agents are non-deterministic across runs; the validation grid is the discipline that catches drift.

**Scope flags (4):**
- `bundling_risk` (high) — drone + timelapse + photography + ISL bundled with a four-formats elimination rule.
- `unusual_sample_requirement` (high) — exactly 4 examples / one per format / ≤3 min / ≥1 with interviews / ≥1 public-infrastructure.
- `qualification_overreach` (medium) — supplier-pays-upfront clause disadvantages smaller suppliers.
- `spec_drift_from_market` (medium) — long-duration timelapse is a specialist sub-market being bundled into a generalist AV framework.

The `qualification_overreach` and `spec_drift_from_market` flags are particularly strong: neither was in the system prompt; the agent identified them from the profile.

**Recommendations (3, closed taxonomy):**
- `SPLIT_TENDER` (high) — split into (a) drone+video+photography+ISL, (b) long-duration timelapse. Cites the drone-specialist comparable (7 responses) and timelapse-specialist (5 responses) as evidence.
- `TIGHTEN_QUALIFICATION` (high) — *interesting use* — the agent is actually proposing to **relax** the rigid 4-format rule ("exactly 4" → "at least 4", allow format substitution). The closed taxonomy doesn't have `LOOSEN_QUALIFICATION`, so the agent picked the closest match. This is a finding for the demo: the taxonomy is the load-bearing constraint, and this run reveals an obvious extension.
- `PIN_RFI_FIRST` (medium) — pre-publication market sounding given the undefined value band and three-sub-market bundle.

**Executive summary** (118 words): leads with the dominant risk (the four-format rule plus bundling), names the forecast range explicitly, references each flag by kind, concludes with the three recommended actions. Concrete throughout.

## Demo exhibits this session unlocks

1. **End-to-end run timing** (~71 s, ~$1.14) reads well: this is not a 10-minute job, it's a coffee-break artefact.
2. **Audit chain** is real — three records linked, each reconstructable end-to-end.
3. **Taxonomy stretch** as a self-discovered finding: the agent's use of `TIGHTEN_QUALIFICATION` to mean "rework" suggests we need to widen the taxonomy in the next iteration — exactly the kind of feedback loop a CTO will appreciate.
4. **Calibration drift between runs** (12-30 high vs 15-30 medium for the same forecast) makes the case for the validation grid as the next session's priority.

## What's next (session 005)

The validation grid: take `reports/drone-report.json`, score every quantitative prediction against the known outcome in `samples/Drone/`. Display predicted vs actual side-by-side. This is the credibility instrument for the Declan demo.
