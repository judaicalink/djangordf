"""Tests for djangordf.skos (minimal CURIE table in this milestone)."""
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
