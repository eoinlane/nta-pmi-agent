"""CLI: launch the Streamlit UI.

Usage:
    uv run pmi-ui

Equivalent to:
    streamlit run src/pmi_agent/ui/app.py

This wrapper exists so a fresh contributor doesn't have to remember
the path to the app module.
"""

from __future__ import annotations

import sys
from importlib import resources

from streamlit.web import cli as stcli


def main() -> int:
    app_path = resources.files("pmi_agent.ui") / "app.py"
    sys.argv = ["streamlit", "run", str(app_path)]
    return stcli.main()  # type: ignore[no-any-return]


if __name__ == "__main__":
    raise SystemExit(main())
