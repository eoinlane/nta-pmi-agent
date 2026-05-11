"""Load a .docx tender into a structured-text representation suitable for LLM input.

The Spec Analyser sees a markdown-ish flattening that preserves heading
levels and table structure in document order. The file's SHA-256 hash
is returned alongside the text and lands in the ProvenanceRecord — so
every claim derived from this input can be tied back to the exact bytes
that produced it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


@dataclass(frozen=True)
class LoadedDocument:
    structured_text: str
    sha256: str
    source_path: Path


def load_docx(path: Path) -> LoadedDocument:
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()

    doc = Document(str(path))
    chunks: list[str] = []

    for child in doc.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            text = _render_paragraph(Paragraph(child, doc._body))
            if text:
                chunks.append(text)
        elif tag == "tbl":
            text = _render_table(Table(child, doc._body))
            if text:
                chunks.append(text)

    return LoadedDocument(
        structured_text="\n\n".join(chunks),
        sha256=sha,
        source_path=path,
    )


def _render_paragraph(para: Paragraph) -> str:
    text = para.text.strip()
    if not text:
        return ""

    style = para.style.name if para.style else ""
    if style.startswith("Heading"):
        try:
            level = int(style.split()[-1])
            level = max(1, min(level, 6))
        except (ValueError, IndexError):
            level = 2
        return f"{'#' * level} {text}"

    if style == "Title":
        return f"# {text}"

    return text


def _render_table(tbl: Table) -> str:
    rows: list[str] = []
    for row in tbl.rows:
        cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        rows.append(" | ".join(cells))
    return "\n".join(rows)
