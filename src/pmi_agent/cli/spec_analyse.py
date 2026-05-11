"""CLI entry point: run the Spec Analyser against a single tender file.

Usage:
    uv run pmi-spec-analyse path/to/tender.docx [--output out.json]

`path` may be absolute, relative to the current dir, or relative to
SAMPLES_DIR (in that lookup order).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from pmi_agent.agents.spec_analyser import analyse_spec
from pmi_agent.audit import open_audit_log


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
    raise FileNotFoundError(
        f"Could not find tender file: {path_arg}\n"
        f"  Tried: {candidate.resolve()}\n"
        f"  And:   {Path(samples) / path_arg if samples else '<SAMPLES_DIR unset>'}"
    )


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Extract a structured RequirementsProfile from a draft tender.",
    )
    parser.add_argument(
        "path",
        help="Path to the tender .docx (absolute, cwd-relative, or SAMPLES_DIR-relative).",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Write the RequirementsProfile JSON here (default: stdout).",
    )
    args = parser.parse_args()

    try:
        path = _resolve(args.path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Analysing: {path}", file=sys.stderr)

    with open_audit_log() as audit:
        result = analyse_spec(path, audit=audit)

    print(f"Audit record: {result.audit_record_id}", file=sys.stderr)

    payload = result.profile.model_dump_json(indent=2)
    if args.output:
        Path(args.output).write_text(payload)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
