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
