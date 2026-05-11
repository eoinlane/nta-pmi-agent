"""seed_loader: the JSON file parses, every record validates as ComparableTender."""

from pmi_agent.data.seed_loader import load_comparables, load_raw_seed
from pmi_agent.schemas import ComparableTender, SourceKind


def test_seed_file_is_clearly_labelled_synthetic() -> None:
    raw = load_raw_seed()
    assert raw["_meta"]["synthetic"] is True
    assert "production_note" in raw["_meta"]


def test_seed_loads_as_typed_comparable_tenders() -> None:
    comparables = load_comparables()

    assert len(comparables) >= 5
    assert all(isinstance(c, ComparableTender) for c in comparables)
    assert all(c.source.kind is SourceKind.CURATED_SEED for c in comparables)


def test_seed_covers_a_range_of_response_volumes() -> None:
    """The seed needs both small-pool and large-pool examples so the agent
    can express bundling effects in its forecast."""
    counts = [c.response_count for c in load_comparables() if c.response_count]
    assert min(counts) <= 10
    assert max(counts) >= 25
