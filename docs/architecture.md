# Architecture

The Pre-Market Intelligence Agent reads a draft tender, runs four cooperating agents, and produces a Pre-Market Intelligence Report. Every agent call is audit-logged. The Recommendation Agent's output is constrained to a closed taxonomy so the system cannot invent free-form advice that reads as authoritative but isn't grounded.

```mermaid
flowchart TD
    %% Input
    DOC[("Draft tender .docx")]:::input

    %% Loader
    LOADER["docx_loader<br/>SHA-256 + structured text"]:::built

    %% Agents
    SPEC["<b>Spec Analyser</b><br/>Claude · forced tool use<br/>→ RequirementsProfile"]:::built
    HIST["<b>Historical Analyst</b><br/>→ ResponseVolumeForecast<br/>range + Confidence + N="]:::tbd
    MARKET["<b>Market Scanner</b>"]:::deferred
    REC["<b>Recommendation Agent</b><br/>closed taxonomy<br/>→ PreMarketReport"]:::tbd

    %% Data sources
    TED[("TED API<br/>live, public")]:::source
    SEED[("historical_seed.json<br/>hand-curated, in repo")]:::source

    %% Output + actor
    UI["Streamlit UI · PDF report"]:::tbd
    OFFICER(["Procurement officer<br/>cites in approval form"]):::actor

    %% Cross-cutting
    AUDIT[("<b>audit.db</b><br/>SQLite · every agent call<br/>prompts · tool input · tokens<br/>duration · error · UUID")]:::audit
    GT[("Historical procurement<br/>artefacts (local only)")]:::input
    VG["<b>Validation grid</b><br/>predicted vs actual"]:::tbd

    %% Main flow
    DOC -->|user upload| LOADER
    LOADER --> SPEC
    SPEC -->|RequirementsProfile| HIST
    SPEC -.->|RequirementsProfile| MARKET
    TED --> HIST
    SEED --> HIST
    HIST --> REC
    MARKET -.-> REC
    REC -->|PreMarketReport| UI
    UI --> OFFICER

    %% Audit
    SPEC -. logs .-> AUDIT
    HIST -. logs .-> AUDIT
    REC -. logs .-> AUDIT

    %% Validation
    REC --> VG
    GT --> VG

    %% Legend
    subgraph LEGEND [" "]
        direction LR
        L1["✓ Built"]:::built
        L2["TBD"]:::tbd
        L3["Deferred"]:::deferred
        L4["Local-only input"]:::input
        L5["External data source"]:::source
        L6["Audit"]:::audit
    end

    classDef built fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px,color:#000
    classDef tbd fill:#fff3cd,stroke:#856404,stroke-width:2px,color:#000
    classDef deferred fill:#e0e0e0,stroke:#616161,stroke-width:1px,stroke-dasharray:5 5,color:#000
    classDef input fill:#ffcdd2,stroke:#c62828,stroke-width:2px,color:#000
    classDef source fill:#bbdefb,stroke:#1565c0,stroke-width:1px,color:#000
    classDef audit fill:#fff9c4,stroke:#f57f17,stroke-width:2px,color:#000
    classDef actor fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#000
```

## Agents

| Agent | Status | Job |
|---|---|---|
| **Spec Analyser** | Built | Parse draft tender → typed `RequirementsProfile` |
| **Historical Analyst** | In progress | TED + curated seed → `ResponseVolumeForecast` with range and confidence |
| **Market Scanner** | Deferred | Curated supplier index → `MarketDepth` |
| **Recommendation Agent** | In progress | Synthesise into `PreMarketReport`; choose from closed taxonomy of six kinds |

The orchestrator is deterministic — Spec Analyser, then a fan-out to Historical Analyst (and later Market Scanner), then Recommendation. The LLM does thinking inside each agent, never routing.

## Design choices

**Closed-taxonomy recommendations.** The Recommendation Agent selects from `SPLIT_TENDER`, `PIN_RFI_FIRST`, `TIGHTEN_QUALIFICATION`, `GEOGRAPHIC_FILTER`, `VALUE_BAND_REVIEW`, `KEY_PERSONNEL_FILTER`. No free-form recommendation strings. This is the main guard against hallucinated advice.

**Ranges with confidence bands, never point estimates.** `ResponseVolumeForecast` has lower/upper bounds and a `Confidence` (low/med/high). A single predicted-submissions number invites (correctly) immediate pushback.

**Forced tool use for structured extraction.** Each agent's Claude call passes the target Pydantic schema as the `input_schema` of a single tool and forces that tool, so the model must produce a typed object. Pydantic then validates downstream.

**Mandatory provenance.** `RequirementsProfile.provenance` is non-optional. Every claim derived from a tender carries the source file hash, extraction method, and timestamp — so a procurement officer can defend each citation in an approval form.

## Audit log

`audit.db` (SQLite) records one row per agent call: timestamp, agent name, model, full system + user prompts, structured output, response metadata (stop_reason, token usage), duration, and any error. This operationalises the audit-trail control discussed in the broader procurement-AI roadmap.

## Validation

For a closed tender with a known outcome, predictions in `PreMarketReport` are compared against the actual response count, evaluation duration, and award values. This is the credibility instrument — the agent's job is not just to produce a plausible-looking report but to make predictions that survive contact with reality.
