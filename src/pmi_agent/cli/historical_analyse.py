"""CLI: forecast response volume from a previously-extracted RequirementsProfile.

Usage:
    uv run pmi-historical-analyse path/to/spec.json [-o forecast.json]

The input is the JSON produced by `pmi-spec-analyse`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from pmi_agent.agents.historical_analyst import forecast_volume
from pmi_agent.audit import open_audit_log
from pmi_agent.schemas import RequirementsProfile


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description=(
            "Forecast response volume for a draft tender from comparable "
            "awarded contracts."
        ),
    )
    parser.add_argument("spec", help="Path to a RequirementsProfile JSON file.")
    parser.add_argument(
        "-o",
        "--output",
        help="Write the ResponseVolumeForecast JSON here (default: stdout).",
    )
    args = parser.parse_args()

    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"ERROR: file not found: {spec_path}", file=sys.stderr)
        return 1

    profile = RequirementsProfile.model_validate_json(spec_path.read_text())
    print("Forecasting against curated comparables...", file=sys.stderr)

    with open_audit_log() as audit:
        result = forecast_volume(profile, audit=audit)

    print(
        f"Considered {result.comparables_considered} comparables; "
        f"audit record {result.audit_record_id}",
        file=sys.stderr,
    )

    payload = result.forecast.model_dump_json(indent=2)
    if args.output:
        Path(args.output).write_text(payload)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
