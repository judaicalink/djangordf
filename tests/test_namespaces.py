"""Tests for djangordf.namespaces — LangString + NamespaceRegistry."""
import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, SKOS


# -- LangString -------------------------------------------------------------

def test_langstring_holds_value_and_lang():
    from djangordf.namespaces import LangString
    ls = LangString("Buch", "de")
    assert ls.value == "Buch"
    assert ls.lang == "de"


def test_langstring_is_frozen():
    import dataclasses
    from djangordf.namespaces import LangString
    ls = LangString("Buch", "de")
    try:
        ls.value = "Roman"
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("LangString must be frozen")


def test_langstring_equality_by_value_and_lang():
    from djangordf.namespaces import LangString
    assert LangString("Buch", "de") == LangString("Buch", "de")
    assert LangString("Buch", "de") != LangString("Buch", "en")
    assert LangString("Buch", "de") != LangString("Roman", "de")


def test_langstring_is_hashable():
    from djangordf.namespaces import LangString
    s = {LangString("Buch", "de"), LangString("Buch", "de")}
    assert len(s) == 1


# -- NamespaceRegistry ------------------------------------------------------

def test_registry_seeds_default_prefixes():
    from djangordf.namespaces import NamespaceRegistry
    r = NamespaceRegistry()
    bindings = r.bindings()
    for prefix in ("rdf", "rdfs", "owl", "xsd", "skos", "dct", "foaf"):
        assert prefix in bindings


def test_registry_resolve_skos_concept():
    from djangordf.namespaces import NamespaceRegistry
    r = NamespaceRegistry()
    assert r.resolve("skos:Concept") == SKOS.Concept


def test_registry_resolve_rdfs_label():
    from djangordf.namespaces import NamespaceRegistry
    r = NamespaceRegistry()
    assert r.resolve("rdfs:label") == RDFS.label


def test_registry_register_then_resolve_roundtrip():
    from djangordf.namespaces import NamespaceRegistry
    r = NamespaceRegistry()
    r.register("ex", "http://example.org/")
    assert r.resolve("ex:Thing") == URIRef("http://example.org/Thing")


def test_registry_resolve_full_iri_passthrough():
    from djangordf.namespaces import NamespaceRegistry
    r = NamespaceRegistry()
    for iri in (
        "http://example.org/Person",
        "https://example.org/Person",
        "urn:example:thing",
    ):
        assert str(r.resolve(iri)) == iri


def test_registry_resolve_uriref_passthrough():
    from djangordf.namespaces import NamespaceRegistry
    r = NamespaceRegistry()
    uri = URIRef("http://example.org/X")
    assert r.resolve(uri) is uri


def test_registry_resolve_unknown_prefix_raises():
    from djangordf.namespaces import NamespaceRegistry
    r = NamespaceRegistry()
    with pytest.raises(ValueError):
        r.resolve("xxx:Thing")


def test_registry_resolve_non_string_raises_type_error():
    from djangordf.namespaces import NamespaceRegistry
    r = NamespaceRegistry()
    with pytest.raises(TypeError):
        r.resolve(42)


def test_registry_bind_to_graph_binds_defaults():
    from djangordf.namespaces import NamespaceRegistry
    r = NamespaceRegistry()
    g = Graph()
    r.bind_to_graph(g)
    bound = {prefix: str(ns) for prefix, ns in g.namespaces()}
    assert bound["skos"] == str(SKOS)
    assert bound["rdf"] == str(RDF)


def test_module_singleton_registry_is_a_namespace_registry():
    from djangordf.namespaces import NamespaceRegistry, registry
    assert isinstance(registry, NamespaceRegistry)


def test_apply_namespace_settings_with_explicit_extra():
    from djangordf.namespaces import NamespaceRegistry, apply_namespace_settings
    import djangordf.namespaces as ns_mod

    saved = ns_mod.registry
    ns_mod.registry = NamespaceRegistry()
    try:
        apply_namespace_settings({"jl": "http://judaicalink.org/vocab/"})
        assert ns_mod.registry.resolve("jl:Term") == URIRef(
            "http://judaicalink.org/vocab/Term"
        )
    finally:
        ns_mod.registry = saved


def test_apply_namespace_settings_reads_django_setting(settings):
    settings.DJANGORDF_NAMESPACES = {"gnd": "https://d-nb.info/gnd/"}
    from djangordf.namespaces import NamespaceRegistry, apply_namespace_settings
    import djangordf.namespaces as ns_mod

    saved = ns_mod.registry
    ns_mod.registry = NamespaceRegistry()
    try:
        apply_namespace_settings()
        assert ns_mod.registry.resolve("gnd:118540238") == URIRef(
            "https://d-nb.info/gnd/118540238"
        )
    finally:
        ns_mod.registry = saved
