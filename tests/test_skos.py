"""Tests for djangordf.skos."""
import pytest
from rdflib.namespace import SKOS


def test_skos_concept_constant():
    from djangordf.skos import Concept
    assert Concept == SKOS.Concept


def test_resolve_curie_known_prefix():
    from djangordf.skos import resolve_curie
    assert resolve_curie("skos:Concept") == SKOS.Concept


def test_resolve_curie_passes_full_iri_through():
    from djangordf.skos import resolve_curie
    iri = "http://example.org/Person"
    assert str(resolve_curie(iri)) == iri


def test_resolve_curie_unknown_prefix_raises():
    from djangordf.skos import resolve_curie
    with pytest.raises(ValueError):
        resolve_curie("xxx:Thing")


def test_default_predicates_has_all_skos_conventions():
    from djangordf.skos import DEFAULT_PREDICATES
    assert DEFAULT_PREDICATES["pref_label"] == SKOS.prefLabel
    assert DEFAULT_PREDICATES["alt_label"] == SKOS.altLabel
    assert DEFAULT_PREDICATES["hidden_label"] == SKOS.hiddenLabel
    assert DEFAULT_PREDICATES["definition"] == SKOS.definition
    assert DEFAULT_PREDICATES["note"] == SKOS.note
    assert DEFAULT_PREDICATES["broader"] == SKOS.broader
    assert DEFAULT_PREDICATES["narrower"] == SKOS.narrower
    assert DEFAULT_PREDICATES["related"] == SKOS.related
    assert DEFAULT_PREDICATES["exact_match"] == SKOS.exactMatch
    assert DEFAULT_PREDICATES["close_match"] == SKOS.closeMatch
    assert DEFAULT_PREDICATES["in_scheme"] == SKOS.inScheme


def test_default_predicates_count_matches_spec():
    from djangordf.skos import DEFAULT_PREDICATES
    assert len(DEFAULT_PREDICATES) == 11
