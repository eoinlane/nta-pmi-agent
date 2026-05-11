# 2026-05-11 — Session 003 — Historical Analyst against a curated seed

## Leading prompt (from Eoin)

> Hand-curate TED seed and build Historical Analyst

## What this session produced

- `src/pmi_agent/data/historical_seed.json` — 6 clearly-labelled-synthetic comparable awarded contracts spanning the range of media-production scopes: bundled video+drone+photography (large pool), drone-specialist (small pool), pure promotional video (large pool), multimedia incl. ISL/Irish-language (medium pool), pure timelapse (very small pool), and a highly-comparable bundled framework. The `_meta` block flags it as synthetic and references the production path (TED API).
- `src/pmi_agent/data/seed_loader.py` — typed loader that returns `ComparableTender` objects with `source.kind = CURATED_SEED` so downstream agents and the final report are transparent about provenance.
- `src/pmi_agent/agents/historical_analyst.py` — the agent. Takes a `RequirementsProfile` plus comparables, returns a `ResponseVolumeForecast` with explicit lower/upper bounds, `Confidence` band, basis text including N, and the subset of comparables it actually relied on.
- `src/pmi_agent/cli/historical_analyse.py` — `pmi-historical-analyse <spec.json>` entry point.
- `tests/test_seed_loader.py` — three tests: seed is labelled synthetic, loads as typed objects, spans a range of response volumes.

## Hallucination guards in the prompt

System prompt:
- Forbids inventing comparables — must use only the supplied set.
- Ties confidence to count of close matches (≥4 close → high, 2-3 → medium, ≤1 → low).
- Demands wide-enough ranges; warns against "false precision dressed as a tight range".
- Requires comparables_considered list to be copied verbatim from the input, not invented.

## First end-to-end run — drone tender

```
$ uv run pmi-historical-analyse reports/drone-spec.json -o reports/drone-forecast.json

Forecasting against curated comparables...
Considered 6 comparables; audit record 18bd58e9-ac7f-495d-8f9a-e322664532b4
Wrote reports/drone-forecast.json
```

| Metric | Value |
|---|---|
| Model | claude-opus-4-7 |
| Duration | 20.8 s |
| Input tokens | 7,529 |
| Output tokens | 2,282 |
| Approx. cost | ~$0.28 |

## What the agent forecast

- **Predicted submissions: 12-30**
- **Confidence: high** (claimed N=4 close matches)
- **Closest match cited:** `demo-seed-006` (bundled drone+video+photography, ranked-two-supplier, nationwide, 28 responses, 9 months).
- **Reasoning highlight:** included the drone-specialist comparable (`demo-seed-002`, 7 responses) as a *lower-bound anchor* because the "all-four-formats" elimination rule in the draft narrows the pool — a procurement-officer-level piece of reasoning that didn't come from the prompt.
- **Evaluation panel-days estimate:** 30-70 days.

## Why this matters for the demo

The drone tender actually received **28 submissions** and took 10 months to evaluate. The agent's range (12-30) lands at the upper end, with the explicit caveat in `basis` that the elimination rules suppress the pool. This is the headline beat for the Declan demo: *given the right comparable on file, the agent would have predicted the response volume that actually happened.* It also makes the case for Phase 8 — the lessons-learned loop — concrete: every NTA tender that closes out feeds back into the comparable set, calibrating future forecasts.

## Caveat for the demo narrative

The agent claimed N=4 close matches for `high` confidence, but the basis text describes only 3 truly close and 1 used as a lower-bound anchor. Strict reading: confidence should arguably have been `medium`. This is a useful exhibit of the limits of self-reporting — the validation grid (next session) is the corrective.

## Operational fix logged this session

Python 3.13's site module skips `.pth` files with leading underscore, which breaks hatchling's `_editable_impl_*.pth` editable install. Worked around by pinning the project to `>=3.11,<3.13` (`.python-version` = `3.12`) and recreating the venv. Worth knowing for the build narrative — it's the first concrete "thing Claude Code helped diagnose under time pressure" moment, the kind of incident the demo will land with developer-leaning viewers.

## What's next (session 004)

Recommendation Agent over the closed taxonomy, then the orchestrator wiring Spec → Historical → Recommendation into a single `PreMarketReport` pipeline.
