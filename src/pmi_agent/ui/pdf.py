"""Markdown → PDF via pandoc + a PDF engine.

The CLAUDE.md notes that the project's existing rendering workflow is
pandoc + prince. We try those first and fall back through the other
engines pandoc supports. If none is available, returns None so the UI
can surface "install pandoc + prince for PDF export".
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

_PDF_ENGINES = ["prince", "weasyprint", "wkhtmltopdf", "xelatex", "pdflatex"]


def pandoc_available() -> bool:
    return shutil.which("pandoc") is not None


def available_pdf_engine() -> str | None:
    for engine in _PDF_ENGINES:
        if shutil.which(engine):
            return engine
    return None


def markdown_to_pdf(markdown: str, *, timeout_seconds: int = 30) -> bytes | None:
    """Return the PDF bytes, or None if pandoc / no engine is available."""
    if not pandoc_available():
        return None
    engine = available_pdf_engine()
    if engine is None:
        return None

    with tempfile.TemporaryDirectory() as tmp:
        md_path = Path(tmp) / "report.md"
        pdf_path = Path(tmp) / "report.pdf"
        md_path.write_text(markdown)
        try:
            subprocess.run(
                [
                    "pandoc",
                    str(md_path),
                    "-o",
                    str(pdf_path),
                    f"--pdf-engine={engine}",
                    "--metadata",
                    "title=Pre-Market Intelligence Report",
                ],
                check=True,
                capture_output=True,
                timeout=timeout_seconds,
            )
            return pdf_path.read_bytes()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None
