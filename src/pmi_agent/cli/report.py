"""CLI: run the full pipeline from a draft tender .docx to a PreMarketReport.

Usage:
    uv run pmi-report path/to/tender.docx [--output report.json]

Resolves `path` via cwd then SAMPLES_DIR. Writes the assembled
PreMarketReport JSON; the executive summary, scope flags, and
recommendations are printed to stderr alongside the audit-record
chain so the operator can spot-check without opening the JSON.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from pmi_agent.audit import open_audit_log
from pmi_agent.orchestrator import generate_report


def _resolve(path_arg: str) -> Path:
    candidate = Path(path_arg)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    if candidate.exists():
        return candidate.resolve()
    samples = os.getenv("SAMPLES_DIR")
    if samples:
        in_samples = Path(samples) / path_arg
        if in_samples.exists():
            return in_samples
    raise FileNotFoundError(f"Could not find tender file: {path_arg}")


def _print_summary(result, file) -> None:
    report = result.report
    print(file=file)
    print("=" * 72, file=file)
    print("EXECUTIVE SUMMARY", file=file)
    print("=" * 72, file=file)
    if report.executive_summary:
        print(report.executive_summary, file=file)
    if report.response_volume_forecast:
        f = report.response_volume_forecast
        print(file=file)
        print(
            f"Forecast: {f.predicted_submissions_lower}-"
            f"{f.predicted_submissions_upper} submissions "
            f"({f.confidence.value} confidence)",
            file=file,
        )
    print(file=file)
    print(f"Scope flags ({len(report.scope_flags)}):", file=file)
    for flag in report.scope_flags:
        print(f"  - [{flag.severity.value}] {flag.kind.value}: {flag.description}", file=file)
    print(file=file)
    print(f"Recommendations ({len(report.recommendations)}):", file=file)
    for rec in report.recommendations:
        print(f"  - [{rec.priority.value}] {rec.kind.value}", file=file)
        print(f"      {rec.rationale}", file=file)
    print(file=file)
    print("Audit records:", file=file)
    for agent, audit_id in result.audit_record_ids.items():
        print(f"  {agent:24s} {audit_id}", file=file)
    print("=" * 72, file=file)


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Run the full Pre-Market Intelligence pipeline on a draft tender.",
    )
    parser.add_argument(
        "path",
        help="Path to the tender .docx (absolute, cwd-relative, or SAMPLES_DIR-relative).",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Write the PreMarketReport JSON here (default: stdout JSON, summary on stderr).",
    )
    args = parser.parse_args()

    try:
        path = _resolve(args.path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Running pipeline on: {path}", file=sys.stderr)

    with open_audit_log() as audit:
        result = generate_report(path, audit=audit)

    payload = result.report.model_dump_json(indent=2)
    if args.output:
        Path(args.output).write_text(payload)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(payload)

    _print_summary(result, sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
