"""Streamlit app — load or run a PreMarketReport, view it, export it.

Two operating modes:

- **Cached** (default, demo-safe): load a previously-generated report
  JSON from `reports/`. Instant.
- **Live**: upload a draft tender .docx and run the full pipeline
  (Spec Analyser → Historical Analyst → Recommendation Agent). Roughly
  70 seconds and ~$1.14 on Opus 4.7 at time of writing.

If a matching `TenderActuals` ground-truth file is selected, the
validation grid is shown alongside the report and included in the
markdown / PDF export.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from pmi_agent.audit import open_audit_log
from pmi_agent.orchestrator import generate_report
from pmi_agent.rendering import report_to_markdown
from pmi_agent.schemas import PreMarketReport
from pmi_agent.ui.pdf import available_pdf_engine, markdown_to_pdf, pandoc_available
from pmi_agent.validation import (
    TenderActuals,
    grid_to_markdown,
    validate_report,
)

load_dotenv()

REPORTS_DIR = Path("reports")
GROUND_TRUTH_DIR = REPORTS_DIR / "ground-truth"
AUDIT_DB = Path("audit.db")


def _safe_filename(title: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in title.lower())[:60].strip("-")

st.set_page_config(
    page_title="NTA Pre-Market Intelligence Agent",
    layout="wide",
)


# --------------------------------------------------------------------- #
# State                                                                 #
# --------------------------------------------------------------------- #

if "report" not in st.session_state:
    st.session_state.report = None
if "validation" not in st.session_state:
    st.session_state.validation = None
if "loaded_from" not in st.session_state:
    st.session_state.loaded_from = None


# --------------------------------------------------------------------- #
# Sidebar                                                               #
# --------------------------------------------------------------------- #

with st.sidebar:
    st.markdown("# Pre-Market Intelligence Agent")
    st.caption("NTA · Phase 1 reference build")

    mode = st.radio(
        "Mode",
        ["Cached report", "Live pipeline run"],
        index=0,
        help=(
            "Cached is demo-safe (instant). "
            "Live runs the full pipeline (~70 s, ~$1.14 on Opus 4.7)."
        ),
    )

    st.divider()

    if mode == "Cached report":
        report_files = sorted(REPORTS_DIR.glob("*-report.json")) if REPORTS_DIR.exists() else []
        if not report_files:
            st.warning(
                "No reports in `reports/`. Run `pmi-report <docx>` first, or switch to Live mode."
            )
        else:
            choice = st.selectbox(
                "Report",
                report_files,
                format_func=lambda p: p.name,
            )
            if st.button("Load report", type="primary"):
                report = PreMarketReport.model_validate_json(choice.read_text())
                st.session_state.report = report
                st.session_state.loaded_from = choice.name
                st.session_state.validation = None
                st.rerun()

    else:  # Live
        uploaded = st.file_uploader(
            "Draft tender (.docx)",
            type=["docx"],
            help="The agent does not store this file beyond the session.",
        )
        if uploaded is not None and st.button("Run pipeline", type="primary"):
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                tmp.write(uploaded.read())
                tmp_path = Path(tmp.name)

            progress = st.empty()
            spinner_msg = (
                "Running pipeline — Spec Analyser → Historical Analyst → Recommendation Agent"
            )
            with st.spinner(spinner_msg):
                progress.info("Spec Analyser …")
                with open_audit_log() as audit:
                    result = generate_report(tmp_path, audit=audit)
                progress.success("Done.")

            st.session_state.report = result.report
            st.session_state.loaded_from = uploaded.name
            st.session_state.validation = None
            st.rerun()

    st.divider()
    st.caption("Validation")
    actuals_files = (
        sorted(GROUND_TRUTH_DIR.glob("*-actuals.json"))
        if GROUND_TRUTH_DIR.exists()
        else []
    )
    if actuals_files and st.session_state.report is not None:
        chosen_actuals = st.selectbox(
            "Ground-truth actuals",
            ["— none —"] + [a.name for a in actuals_files],
            help="Score the report against a closed-tender outcome.",
        )
        if chosen_actuals != "— none —" and st.button("Score against actuals"):
            actuals_path = GROUND_TRUTH_DIR / chosen_actuals
            actuals = TenderActuals.model_validate_json(actuals_path.read_text())
            st.session_state.validation = validate_report(
                st.session_state.report, actuals
            )
            st.rerun()

    if st.session_state.loaded_from:
        st.divider()
        st.caption(f"Loaded: `{st.session_state.loaded_from}`")


# --------------------------------------------------------------------- #
# Main panel                                                            #
# --------------------------------------------------------------------- #

report: PreMarketReport | None = st.session_state.report
validation = st.session_state.validation

if report is None:
    st.title("Pre-Market Intelligence Agent")
    st.markdown(
        "Load a cached report from the sidebar, or upload a draft tender and "
        "run the full pipeline live."
    )
    st.stop()


st.title(report.tender.title)
st.caption(
    f"{report.tender.contracting_authority} · "
    f"generated {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}"
)

tabs = st.tabs(
    [
        "Summary",
        "Forecast",
        "Scope flags",
        "Recommendations",
        "Tender profile",
        "Validation",
        "Audit",
        "Export",
    ]
)

# --- Summary tab --- #
with tabs[0]:
    if report.executive_summary:
        st.markdown(report.executive_summary)
    forecast = report.response_volume_forecast
    if forecast:
        cols = st.columns(3)
        cols[0].metric(
            "Predicted submissions",
            f"{forecast.predicted_submissions_lower}-{forecast.predicted_submissions_upper}",
        )
        cols[1].metric("Confidence", forecast.confidence.value)
        cols[2].metric(
            "Comparables used",
            len(forecast.comparable_tenders) if forecast.comparable_tenders else 0,
        )
    cols2 = st.columns(2)
    cols2[0].metric("Scope flags", len(report.scope_flags))
    cols2[1].metric("Recommendations", len(report.recommendations))


# --- Forecast tab --- #
with tabs[1]:
    if forecast := report.response_volume_forecast:
        st.subheader("Response volume")
        cols = st.columns(2)
        cols[0].metric(
            "Predicted submissions",
            f"{forecast.predicted_submissions_lower}-{forecast.predicted_submissions_upper}",
        )
        cols[1].metric("Confidence", forecast.confidence.value)
        if forecast.evaluation_panel_days_lower is not None:
            st.metric(
                "Evaluation effort (panel-days)",
                f"{forecast.evaluation_panel_days_lower}-{forecast.evaluation_panel_days_upper}",
            )
        st.markdown("**Basis**")
        st.markdown(forecast.basis)

        if forecast.comparable_tenders:
            st.subheader("Comparables used")
            for comp in forecast.comparable_tenders:
                with st.expander(f"{comp.source.identifier} — {comp.title}"):
                    st.markdown(f"**Contracting authority:** {comp.contracting_authority}")
                    if comp.awarded_date:
                        st.markdown(f"**Awarded:** {comp.awarded_date.strftime('%Y-%m-%d')}")
                    if comp.response_count is not None:
                        st.markdown(f"**Responses:** {comp.response_count}")
                    if comp.evaluation_duration_months is not None:
                        st.markdown(
                            f"**Evaluation duration:** {comp.evaluation_duration_months} months"
                        )
                    if comp.scope_summary:
                        st.markdown(f"**Scope:** {comp.scope_summary}")
                    st.caption(f"Source: {comp.source.kind.value} / {comp.source.identifier}")
    else:
        st.info("No forecast in this report.")


# --- Scope flags tab --- #
_SEVERITY_BADGE = {"low": "🟢", "medium": "🟡", "high": "🔴"}

with tabs[2]:
    if not report.scope_flags:
        st.info("No scope flags raised.")
    for flag in report.scope_flags:
        badge = _SEVERITY_BADGE.get(flag.severity.value, "")
        with st.container(border=True):
            st.markdown(
                f"**{badge} {flag.kind.value}** · severity: `{flag.severity.value}`"
            )
            st.markdown(flag.description)
            st.markdown(f"> {flag.evidence_quote}")


# --- Recommendations tab --- #
_PRIORITY_BADGE = {"low": "🟢", "medium": "🟡", "high": "🔴"}

with tabs[3]:
    if not report.recommendations:
        st.info("No recommendations.")
    for rec in report.recommendations:
        badge = _PRIORITY_BADGE.get(rec.priority.value, "")
        with st.container(border=True):
            st.markdown(
                f"**{badge} {rec.kind.value}** · priority: `{rec.priority.value}`"
            )
            st.markdown(rec.rationale)
            if rec.evidence_refs:
                st.caption("Evidence: " + ", ".join(rec.evidence_refs))


# --- Tender profile tab --- #
with tabs[4]:
    profile = report.tender
    st.subheader("Summary")
    st.markdown(profile.summary)

    cols = st.columns(2)
    cols[0].markdown(f"**Reference:** {profile.reference or '—'}")
    cols[0].markdown(f"**Award structure:** `{profile.award_structure.value}`")
    cols[0].markdown(f"**Suppliers sought:** {profile.num_suppliers_sought or '—'}")
    cols[1].markdown(f"**Geographic scope:** {profile.geographic_scope or '—'}")
    cols[1].markdown(
        f"**Contract duration:** {profile.contract_duration_months or '—'} months "
        f"(+ extension: {profile.contract_extension_months or '—'} months)"
    )

    if profile.service_categories:
        st.markdown("**Service categories:**")
        for cat in profile.service_categories:
            st.markdown(f"- {cat}")

    if profile.qualification_barriers:
        st.markdown("**Qualification barriers:**")
        for qb in profile.qualification_barriers:
            threshold = f" *({qb.threshold})*" if qb.threshold else ""
            st.markdown(f"- **{qb.kind.value}**{threshold} — {qb.description}")

    if profile.unusual_requirements:
        st.markdown("**Unusual requirements:**")
        for req in profile.unusual_requirements:
            st.markdown(f"- {req}")

    if profile.evaluation_criteria:
        st.markdown("**Evaluation criteria:**")
        for ec in profile.evaluation_criteria:
            weight = f" — **{ec.weight_pct}%**" if ec.weight_pct else ""
            st.markdown(f"- {ec.name}{weight}")
            if ec.description:
                st.caption(ec.description)


# --- Validation tab --- #
with tabs[5]:
    if validation is None:
        st.info(
            "No validation grid loaded. Select a ground-truth actuals file in "
            "the sidebar and click **Score against actuals**."
        )
    else:
        st.markdown(grid_to_markdown(validation))


# --- Audit tab --- #
with tabs[6]:
    st.subheader("Agent audit chain")
    if not AUDIT_DB.exists():
        st.info(f"No audit database at `{AUDIT_DB}`.")
    else:
        ids = report.audit_record_ids
        if not ids:
            st.info("No audit record IDs in this report.")
        else:
            placeholders = ",".join("?" * len(ids))
            conn = sqlite3.connect(AUDIT_DB)
            try:
                rows = conn.execute(
                    f"SELECT id, timestamp, agent, model, duration_ms, response_meta "
                    f"FROM agent_calls WHERE id IN ({placeholders})",
                    ids,
                ).fetchall()
            finally:
                conn.close()
            for row in rows:
                rid, ts, agent_name, model, dur, meta_str = row
                meta = json.loads(meta_str) if meta_str else {}
                usage = meta.get("usage", {})
                with st.expander(f"{agent_name} · {dur/1000:.1f}s · {rid}"):
                    st.markdown(f"**Timestamp:** {ts}")
                    st.markdown(f"**Model:** `{model}`")
                    st.markdown(
                        f"**Tokens:** {usage.get('input_tokens', 0):,} in / "
                        f"{usage.get('output_tokens', 0):,} out"
                    )
                    st.markdown(f"**Stop reason:** `{meta.get('stop_reason')}`")


# --- Export tab --- #
with tabs[7]:
    markdown = report_to_markdown(report, validation=validation)

    cols = st.columns(2)
    cols[0].download_button(
        "Download Markdown",
        markdown,
        file_name=_safe_filename(report.tender.title) + ".md",
        mime="text/markdown",
        type="primary",
    )

    if pandoc_available() and available_pdf_engine():
        pdf_bytes = markdown_to_pdf(markdown)
        if pdf_bytes:
            cols[1].download_button(
                "Download PDF",
                pdf_bytes,
                file_name=_safe_filename(report.tender.title) + ".pdf",
                mime="application/pdf",
            )
        else:
            cols[1].warning("PDF generation failed; download Markdown instead.")
    else:
        cols[1].caption(
            "PDF export needs `pandoc` and a PDF engine (prince, weasyprint, "
            "wkhtmltopdf, or xelatex). Install via Homebrew."
        )

    st.divider()
    st.subheader("Preview")
    st.markdown(markdown)
