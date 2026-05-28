"""Tests for djangordf.properties (minimal base in this milestone)."""
from rdflib import URIRef


def test_property_stores_predicate():
    from djangordf.properties import Property
    p = Property(predicate=URIRef("http://example.org/p"))
    assert p.predicate == URIRef("http://example.org/p")


def test_property_predicate_defaults_to_none():
    from djangordf.properties import Property
    p = Property()
    assert p.predicate is None


def test_contribute_to_class_records_attribute_name():
    from djangordf.properties import Property
    p = Property()
    p.contribute_to_class("pref_label")
    assert p.attr_name == "pref_label"


def test_property_to_rdf_emits_no_triples_for_none_value():
    from rdflib import URIRef
    from djangordf.properties import Property
    p = Property(predicate=URIRef("http://example.org/p"))
    triples = p.to_rdf(URIRef("http://example.org/s"), None)
    assert triples == []


def test_property_from_rdf_returns_none_when_no_match():
    from rdflib import Graph, URIRef
    from djangordf.properties import Property
    p = Property(predicate=URIRef("http://example.org/p"))
    assert p.from_rdf(Graph(), URIRef("http://example.org/s")) is None


def test_property_contribute_to_class_accepts_owner_class():
    from djangordf.properties import Property
    p = Property()
    p.contribute_to_class("title", owner_class=object)
    assert p.attr_name == "title"
    assert p.owner_class is object
