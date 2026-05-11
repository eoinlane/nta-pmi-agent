# 2026-05-11 — Session 007 — Ground-truth refinement against the procurement pack

## Leading prompt (from Eoin)

> what is the curated ground truth and how did you get it?
> [followed by]
> yes do it please

After session 005 (the validation grid) shipped, the question was whether the ground-truth file behind it was actually anchored in the closed tender's procurement pack or just in the headline numbers stated in a workshop. Honest answer: the file's `notes` fields had been reasoned from headline numbers + procurement-domain logic, with file references that hadn't actually been opened.

## What this session did

Read the closed tender's procurement pack end-to-end:

- **Procurement Report** — narrative summary with the formal Lessons Learned section, the decision-record table for choice-of-procedure / use-of-lots / abnormally-low investigations, and the bidder-by-stage outcome table.
- **Tender Compliance Sheet** — per-bidder compliance status (Form of Tender / Article 57 / Selection Criteria / Quality Submission / Price Submission) with sign-off date.
- **Selection Board Report Final** — scoring summary across bidders × criteria, pricing analysis sheets (with and without abnormally-high outliers), per-evaluator scoring.
- **Assessment Notes Final** — per-bidder evaluator notes against each selection criterion, including the score awarded.

Rewrote `reports/ground-truth/drone-tender-actuals.json` (local-only) so that every `flag_outcomes` and `recommendation_outcomes` entry now cites a specific table / row reference from the procurement pack rather than reasoning by analogy from headline numbers.

## Headline findings vs the prior ground-truth state

| Field | Before | After (attested) |
|---|---|---|
| Submissions received | 28 (from workshop) | 28 confirmed (27 on time + 1 late by email) |
| Selection-criteria fall-out | 7 (from workshop) | 7 selection-criteria failures + 1 non-compliance = 8 total before award stage |
| Evaluation duration | 10 months (from workshop) | ~6 months from submission to evaluation completion (the "10 months" headline figure likely covers through to contract sign-off, which isn't in the procurement-report dates) |
| Award outcome | "two suppliers, ranked" | Two named suppliers identified; both top-ranked triggered Article 69 abnormally-low-tender investigations; both explanations accepted |
| Pre-tender vs final contract value | unknown | Pre-tender approved value was materially higher than the recalculated maximum (~42% downward revision) — the value-band-review recommendation has clear retrospective backing |

## The one moment that matters most for the demo

The Procurement Report's own **Lessons Learned** section (Table 5) states — in the formal procurement record, signed off by the Procurement Lead — that:

- A preliminary market consultation would have been beneficial prior to publication, both for better price-point estimation and for better visibility of supplier availability.
- A 2-stage procedure should have been used given the volume of submissions received.

These are NTA's own words, in NTA's own document, independently arriving at exactly the recommendations the PMI Agent produced (`PIN_RFI_FIRST`, `SPLIT_TENDER` / restructure-procedure, `VALUE_BAND_REVIEW`). The validation grid now scores those recommendations as "would have helped" with a direct evidence pointer rather than inference. For the Declan demo, this is the most defensible moment in the whole walkthrough: *the procurement team's own lessons-learned and the agent's recommendations agree on what should have been done differently.*

## Honest caveat in the updated ground truth

`qualification_overreach: partial` is now backed by explicit reasoning: 27 of 28 tenders passed initial compliance checks; the supplier-pays-upfront clause cannot be shown to have caused any documented exclusion, only plausibly deterred non-bidders. `key_personnel_filter` (recommended in the most recent agent run) is scored `neutral` — would have helped at the margin but is not in NTA's documented lessons-learned. The validation grid earns its credibility by holding those honest verdicts visible alongside the wins.

## Confidentiality

The procurement pack itself was read locally; nothing from it has been committed to the public repo. The ground-truth JSON references the source files but lives under `reports/ground-truth/` which is gitignored. This prompt-log entry summarises the upgrade at the level of *what changed* and *what it lets us defend* — verbatim NTA-internal text, specific bidder names, and specific contract values stay out.

## What's next (session 008)

Cathal dry-run + book Declan. The build is now functionally complete; the next session is rehearsal.
