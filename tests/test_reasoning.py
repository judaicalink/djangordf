"""Tests for ``djangordf.reasoning`` — RDFS, SKOS, Composite, and command."""
from io import StringIO

import pytest
from rdflib import Literal, URIRef


_RDF_TYPE = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
_RDFS_SUBCLASS_OF = URIRef("http://www.w3.org/2000/01/rdf-schema#subClassOf")
_RDFS_SUBPROP_OF = URIRef("http://www.w3.org/2000/01/rdf-schema#subPropertyOf")
_RDFS_DOMAIN = URIRef("http://www.w3.org/2000/01/rdf-schema#domain")
_RDFS_RANGE = URIRef("http://www.w3.org/2000/01/rdf-schema#range")

_SKOS_BROADER = URIRef("http://www.w3.org/2004/02/skos/core#broader")
_SKOS_NARROWER = URIRef("http://www.w3.org/2004/02/skos/core#narrower")
_SKOS_BROADER_TRANS = URIRef(
    "http://www.w3.org/2004/02/skos/core#broaderTransitive"
)
_SKOS_NARROWER_TRANS = URIRef(
    "http://www.w3.org/2004/02/skos/core#narrowerTransitive"
)
_SKOS_EXACT_MATCH = URIRef("http://www.w3.org/2004/02/skos/core#exactMatch")


@pytest.fixture
def in_memory_backend(settings):
    settings.DJANGORDF_BACKEND = {
        "class": "djangordf.backends.memory.InMemoryBackend",
    }
    settings.DJANGORDF_DEFAULT_NAMESPACE = "http://example.org/d/"
    settings.DJANGORDF_DEFAULT_GRAPH = "http://example.org/g"


def _read_graph(backend, graph_iri):
    return backend.query(
        "CONSTRUCT { ?s ?p ?o } WHERE { "
        f"GRAPH <{graph_iri}> {{ ?s ?p ?o }} }}"
    )


# -- RDFS rules ------------------------------------------------------------

def test_rdfs_subclass_of_transitivity(in_memory_backend):
    from djangordf import conf
    from djangordf.reasoning import RDFSReasoner

    a = URIRef("http://example.org/A")
    b = URIRef("http://example.org/B")
    c = URIRef("http://example.org/C")
    graph = "urn:test:rdfs"
    backend = conf.get_backend()
    backend.add(
        [(a, _RDFS_SUBCLASS_OF, b), (b, _RDFS_SUBCLASS_OF, c)],
        graph=graph,
    )
    new = RDFSReasoner().materialize(
        backend, source_graph=graph, target_graph=graph,
    )
    assert new >= 1
    triples = list(_read_graph(backend, graph))
    assert (a, _RDFS_SUBCLASS_OF, c) in triples


def test_rdfs_type_propagation_through_subclass(in_memory_backend):
    from djangordf import conf
    from djangordf.reasoning import RDFSReasoner

    person = URIRef("http://example.org/Person")
    agent = URIRef("http://example.org/Agent")
    alice = URIRef("http://example.org/alice")
    graph = "urn:test:rdfs-type"
    backend = conf.get_backend()
    backend.add(
        [
            (person, _RDFS_SUBCLASS_OF, agent),
            (alice, _RDF_TYPE, person),
        ],
        graph=graph,
    )
    RDFSReasoner().materialize(
        backend, source_graph=graph, target_graph=graph,
    )
    triples = list(_read_graph(backend, graph))
    assert (alice, _RDF_TYPE, agent) in triples


def test_rdfs_subproperty_propagates_triples(in_memory_backend):
    from djangordf import conf
    from djangordf.reasoning import RDFSReasoner

    name = URIRef("http://example.org/name")
    label = URIRef("http://example.org/label")
    alice = URIRef("http://example.org/alice")
    graph = "urn:test:rdfs-subprop"
    backend = conf.get_backend()
    backend.add(
        [
            (name, _RDFS_SUBPROP_OF, label),
            (alice, name, Literal("Alice")),
        ],
        graph=graph,
    )
    RDFSReasoner().materialize(
        backend, source_graph=graph, target_graph=graph,
    )
    triples = list(_read_graph(backend, graph))
    assert (alice, label, Literal("Alice")) in triples


def test_rdfs_domain_inference(in_memory_backend):
    from djangordf import conf
    from djangordf.reasoning import RDFSReasoner

    person = URIRef("http://example.org/Person")
    knows = URIRef("http://example.org/knows")
    alice = URIRef("http://example.org/alice")
    bob = URIRef("http://example.org/bob")
    graph = "urn:test:rdfs-domain"
    backend = conf.get_backend()
    backend.add(
        [(knows, _RDFS_DOMAIN, person), (alice, knows, bob)],
        graph=graph,
    )
    RDFSReasoner().materialize(
        backend, source_graph=graph, target_graph=graph,
    )
    triples = list(_read_graph(backend, graph))
    assert (alice, _RDF_TYPE, person) in triples


def test_rdfs_range_inference(in_memory_backend):
    from djangordf import conf
    from djangordf.reasoning import RDFSReasoner

    person = URIRef("http://example.org/Person")
    knows = URIRef("http://example.org/knows")
    alice = URIRef("http://example.org/alice")
    bob = URIRef("http://example.org/bob")
    graph = "urn:test:rdfs-range"
    backend = conf.get_backend()
    backend.add(
        [(knows, _RDFS_RANGE, person), (alice, knows, bob)],
        graph=graph,
    )
    RDFSReasoner().materialize(
        backend, source_graph=graph, target_graph=graph,
    )
    triples = list(_read_graph(backend, graph))
    assert (bob, _RDF_TYPE, person) in triples


# -- SKOS rules ------------------------------------------------------------

def test_skos_broader_to_broader_transitive(in_memory_backend):
    from djangordf import conf
    from djangordf.reasoning import SKOSReasoner

    a = URIRef("http://example.org/c/a")
    b = URIRef("http://example.org/c/b")
    graph = "urn:test:skos-broader"
    backend = conf.get_backend()
    backend.add([(a, _SKOS_BROADER, b)], graph=graph)
    SKOSReasoner().materialize(
        backend, source_graph=graph, target_graph=graph,
    )
    triples = list(_read_graph(backend, graph))
    assert (a, _SKOS_BROADER_TRANS, b) in triples


def test_skos_broader_transitive_closure(in_memory_backend):
    from djangordf import conf
    from djangordf.reasoning import SKOSReasoner

    a = URIRef("http://example.org/c/a")
    b = URIRef("http://example.org/c/b")
    c = URIRef("http://example.org/c/c")
    graph = "urn:test:skos-trans"
    backend = conf.get_backend()
    backend.add(
        [(a, _SKOS_BROADER, b), (b, _SKOS_BROADER, c)],
        graph=graph,
    )
    SKOSReasoner().materialize(
        backend, source_graph=graph, target_graph=graph,
    )
    triples = list(_read_graph(backend, graph))
    assert (a, _SKOS_BROADER_TRANS, c) in triples


def test_skos_narrower_transitive(in_memory_backend):
    from djangordf import conf
    from djangordf.reasoning import SKOSReasoner

    a = URIRef("http://example.org/c/a")
    b = URIRef("http://example.org/c/b")
    graph = "urn:test:skos-narrower"
    backend = conf.get_backend()
    backend.add([(a, _SKOS_NARROWER, b)], graph=graph)
    SKOSReasoner().materialize(
        backend, source_graph=graph, target_graph=graph,
    )
    triples = list(_read_graph(backend, graph))
    assert (a, _SKOS_NARROWER_TRANS, b) in triples


def test_skos_exact_match_symmetry(in_memory_backend):
    from djangordf import conf
    from djangordf.reasoning import SKOSReasoner

    a = URIRef("http://example.org/c/a")
    b = URIRef("http://example.org/c/b")
    graph = "urn:test:skos-exact"
    backend = conf.get_backend()
    backend.add([(a, _SKOS_EXACT_MATCH, b)], graph=graph)
    SKOSReasoner().materialize(
        backend, source_graph=graph, target_graph=graph,
    )
    triples = list(_read_graph(backend, graph))
    assert (b, _SKOS_EXACT_MATCH, a) in triples


# -- Composite + idempotence ----------------------------------------------

def test_composite_reasoner_runs_both(in_memory_backend):
    from djangordf import conf
    from djangordf.reasoning import CompositeReasoner, RDFSReasoner, SKOSReasoner

    a = URIRef("http://example.org/A")
    b = URIRef("http://example.org/B")
    c = URIRef("http://example.org/c1")
    d = URIRef("http://example.org/c2")
    graph = "urn:test:composite"
    backend = conf.get_backend()
    backend.add(
        [
            (a, _RDFS_SUBCLASS_OF, b),
            (c, _SKOS_BROADER, d),
        ],
        graph=graph,
    )
    CompositeReasoner(RDFSReasoner(), SKOSReasoner()).materialize(
        backend, source_graph=graph, target_graph=graph,
    )
    triples = list(_read_graph(backend, graph))
    assert (c, _SKOS_BROADER_TRANS, d) in triples
    # The composite reaches a fixpoint without explosion.
    assert len(triples) < 50


def test_composite_reasoner_requires_at_least_one():
    from djangordf.reasoning import CompositeReasoner
    with pytest.raises(ValueError):
        CompositeReasoner()


def test_reasoner_is_idempotent_on_second_run(in_memory_backend):
    from djangordf import conf
    from djangordf.reasoning import SKOSReasoner

    a = URIRef("http://example.org/c/a")
    b = URIRef("http://example.org/c/b")
    graph = "urn:test:skos-idem"
    backend = conf.get_backend()
    backend.add([(a, _SKOS_BROADER, b)], graph=graph)
    reasoner = SKOSReasoner()
    reasoner.materialize(backend, source_graph=graph, target_graph=graph)
    second_pass = reasoner.materialize(
        backend, source_graph=graph, target_graph=graph,
    )
    assert second_pass == 0


def test_reasoner_writes_into_target_graph_only(in_memory_backend):
    from djangordf import conf
    from djangordf.reasoning import RDFSReasoner

    a = URIRef("http://example.org/A")
    b = URIRef("http://example.org/B")
    c = URIRef("http://example.org/C")
    src = "urn:test:src"
    tgt = "urn:test:tgt"
    backend = conf.get_backend()
    backend.add(
        [(a, _RDFS_SUBCLASS_OF, b), (b, _RDFS_SUBCLASS_OF, c)],
        graph=src,
    )
    RDFSReasoner().materialize(
        backend, source_graph=src, target_graph=tgt,
    )
    tgt_triples = list(_read_graph(backend, tgt))
    assert (a, _RDFS_SUBCLASS_OF, c) in tgt_triples


# -- public materialize() entry point --------------------------------------

def test_materialize_resolves_dotted_path(in_memory_backend, settings):
    from djangordf import conf
    from djangordf.reasoning import materialize

    a = URIRef("http://example.org/c/a")
    b = URIRef("http://example.org/c/b")
    graph = "urn:test:mat-dotted"
    backend = conf.get_backend()
    backend.add([(a, _SKOS_BROADER, b)], graph=graph)

    materialize(
        "djangordf.reasoning.SKOSReasoner",
        backend=backend, source_graph=graph, target_graph=graph,
    )
    triples = list(_read_graph(backend, graph))
    assert (a, _SKOS_BROADER_TRANS, b) in triples


def test_materialize_resolves_from_settings(in_memory_backend, settings):
    from djangordf import conf
    from djangordf.reasoning import materialize

    settings.DJANGORDF_REASONER = "djangordf.reasoning.SKOSReasoner"
    a = URIRef("http://example.org/c/a")
    b = URIRef("http://example.org/c/b")
    graph = "urn:test:mat-settings"
    backend = conf.get_backend()
    backend.add([(a, _SKOS_BROADER, b)], graph=graph)

    materialize(
        backend=backend, source_graph=graph, target_graph=graph,
    )
    triples = list(_read_graph(backend, graph))
    assert (a, _SKOS_BROADER_TRANS, b) in triples


def test_materialize_without_reasoner_raises(in_memory_backend, settings):
    from django.core.exceptions import ImproperlyConfigured
    from djangordf.reasoning import materialize

    settings.DJANGORDF_REASONER = None
    with pytest.raises(ImproperlyConfigured):
        materialize()


# -- management command ----------------------------------------------------

def test_reason_command_applies(in_memory_backend, settings):
    from django.core.management import call_command
    from djangordf import conf

    settings.DJANGORDF_REASONER = "djangordf.reasoning.SKOSReasoner"
    a = URIRef("http://example.org/c/a")
    b = URIRef("http://example.org/c/b")
    graph = "urn:test:cmd"
    backend = conf.get_backend()
    backend.add([(a, _SKOS_BROADER, b)], graph=graph)

    buf = StringIO()
    call_command(
        "reason", "--source", graph, "--target", graph, stdout=buf,
    )
    output = buf.getvalue()
    assert "Added" in output or "inferred" in output
    triples = list(_read_graph(backend, graph))
    assert (a, _SKOS_BROADER_TRANS, b) in triples


def test_reason_command_dry_run_leaves_store_untouched(
    in_memory_backend, settings,
):
    from django.core.management import call_command
    from djangordf import conf

    settings.DJANGORDF_REASONER = "djangordf.reasoning.SKOSReasoner"
    a = URIRef("http://example.org/c/a")
    b = URIRef("http://example.org/c/b")
    graph = "urn:test:cmd-dry"
    backend = conf.get_backend()
    backend.add([(a, _SKOS_BROADER, b)], graph=graph)

    buf = StringIO()
    call_command(
        "reason", "--source", graph, "--dry-run", stdout=buf,
    )
    triples = list(_read_graph(backend, graph))
    # The original triple is still there; no transitive triple was written.
    assert (a, _SKOS_BROADER, b) in triples
    assert (a, _SKOS_BROADER_TRANS, b) not in triples


def test_reason_command_without_reasoner_raises(in_memory_backend, settings):
    from django.core.management import call_command
    from django.core.management.base import CommandError

    settings.DJANGORDF_REASONER = None
    with pytest.raises(CommandError):
        call_command("reason")


# -- importable -----------------------------------------------------------

def test_reasoning_public_api_is_importable():
    from djangordf.reasoning import (
        CompositeReasoner,
        RDFSReasoner,
        Reasoner,
        SKOSReasoner,
        materialize,
    )
    for cls in (Reasoner, RDFSReasoner, SKOSReasoner, CompositeReasoner):
        assert callable(cls)
    assert callable(materialize)
