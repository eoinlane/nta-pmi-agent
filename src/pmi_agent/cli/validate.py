"""CLI: validate a PreMarketReport against ground-truth actuals.

Usage:
    uv run pmi-validate path/to/report.json path/to/actuals.json [-o out.md]

The actuals file is a TenderActuals JSON document (hand-curated from the
closed tender's procurement pack). The output is a markdown table that
scores quantitative predictions, scope flags, recommendations, and
flags false negatives.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from pmi_agent.schemas import PreMarketReport
from pmi_agent.validation import (
    TenderActuals,
    grid_to_markdown,
    validate_report,
)


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Validate a PreMarketReport against ground-truth tender actuals.",
    )
    parser.add_argument("report", help="Path to the PreMarketReport JSON.")
    parser.add_argument("actuals", help="Path to the TenderActuals JSON.")
    parser.add_argument(
        "-o",
        "--output",
        help="Write the validation grid markdown here (default: stdout).",
    )
    args = parser.parse_args()

    report_path = Path(args.report)
    actuals_path = Path(args.actuals)
    if not report_path.exists():
        print(f"ERROR: report not found: {report_path}", file=sys.stderr)
        return 1
    if not actuals_path.exists():
        print(f"ERROR: actuals not found: {actuals_path}", file=sys.stderr)
        return 1

    report = PreMarketReport.model_validate_json(report_path.read_text())
    actuals = TenderActuals.model_validate_json(actuals_path.read_text())

    grid = validate_report(report, actuals)
    markdown = grid_to_markdown(grid)

    if args.output:
        Path(args.output).write_text(markdown)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(markdown)

    print(file=sys.stderr)
    print("SUMMARY: " + grid.summary, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
