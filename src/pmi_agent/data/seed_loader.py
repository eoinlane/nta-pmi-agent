"""Load the hand-curated historical seed.

The seed is a placeholder for demo purposes — see `historical_seed.json`'s
`_meta.production_note`. The production Historical Analyst queries TED
directly; this loader returns the same `ComparableTender` shape regardless
of source, so swapping in a live TED query is a contained change.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from importlib import resources

from pmi_agent.schemas import ComparableTender, SourceKind, SourceRef


def load_raw_seed() -> dict:
    """Return the parsed JSON file."""
    text = (resources.files("pmi_agent.data") / "historical_seed.json").read_text()
    return json.loads(text)


def load_comparables(now: datetime | None = None) -> list[ComparableTender]:
    """Return the seed as typed ComparableTender objects.

    Each entry's source is tagged `SourceKind.CURATED_SEED` so downstream
    agents and the final report can be transparent about provenance.
    """
    now = now or datetime.now(UTC)
    raw = load_raw_seed()
    return [_to_comparable(record, retrieved_at=now) for record in raw["comparables"]]


def _to_comparable(record: dict, *, retrieved_at: datetime) -> ComparableTender:
    return ComparableTender(
        source=SourceRef(
            kind=SourceKind.CURATED_SEED,
            identifier=record["identifier"],
            title=record["title"],
            snippet=record.get("notes"),
            retrieved_at=retrieved_at,
        ),
        title=record["title"],
        contracting_authority=record["contracting_authority"],
        cpv_codes=record.get("cpv_codes", []),
        value_eur=record.get("awarded_value_eur"),
        awarded_date=_parse_iso_date(record.get("awarded_date")),
        response_count=record.get("response_count"),
        evaluation_duration_months=record.get("evaluation_duration_months"),
        scope_summary=record.get("scope_summary"),
    )


def _parse_iso_date(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(f"{s}T00:00:00+00:00")
