"""Tests for djangordf.backends."""
import warnings

import pytest
from rdflib import Literal, URIRef


EX_S = URIRef("http://example.org/s")
EX_P = URIRef("http://example.org/p")
EX_P2 = URIRef("http://example.org/p2")
EX_G = URIRef("http://example.org/g")


# -- Abstract base ----------------------------------------------------------


def test_triple_store_backend_is_abstract():
    """Instantiating the abstract base must raise TypeError."""
    from djangordf.backends.base import TripleStoreBackend
    with pytest.raises(TypeError):
        TripleStoreBackend()


def test_subclass_must_implement_all_methods():
    """A subclass missing any abstract method cannot be instantiated."""
    from djangordf.backends.base import TripleStoreBackend

    class Partial(TripleStoreBackend):
        def query(self, sparql):
            return None

    with pytest.raises(TypeError):
        Partial()


def test_complete_subclass_can_be_instantiated():
    """A subclass overriding every abstract method works."""
    from djangordf.backends.base import TripleStoreBackend

    class Complete(TripleStoreBackend):
        def query(self, sparql):
            return None

        def update(self, sparql):
            return None

        def add(self, triples, graph=None):
            return None

        def remove(self, pattern, graph=None):
            return None

        def clear(self, graph=None):
            return None

    Complete()


# -- InMemoryBackend --------------------------------------------------------


@pytest.fixture
def backend():
    from djangordf.backends.memory import InMemoryBackend
    return InMemoryBackend()


def test_in_memory_backend_starts_empty(backend):
    result = backend.query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    assert len(result) == 0


def test_in_memory_backend_constructs_without_rdflib_deprecation_warning():
    from djangordf.backends.memory import InMemoryBackend

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        backend = InMemoryBackend()
        backend.add([(EX_S, EX_P, Literal("v"))])
        backend.clear()


def test_add_then_construct_roundtrips_triples(backend):
    backend.add([(EX_S, EX_P, Literal("v"))])
    result = backend.query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    assert (EX_S, EX_P, Literal("v")) in result


def test_update_insert_data(backend):
    backend.update(
        'INSERT DATA { <http://example.org/s> <http://example.org/p> "v" }'
    )
    result = backend.query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    assert len(result) == 1


def test_update_delete_where(backend):
    backend.add([(EX_S, EX_P, Literal("v"))])
    backend.update("DELETE WHERE { ?s ?p ?o }")
    result = backend.query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    assert len(result) == 0


def test_remove_with_subject_pattern_strips_all_matches(backend):
    backend.add([(EX_S, EX_P, Literal("a"))])
    backend.add([(EX_S, EX_P2, Literal("b"))])
    backend.add([(URIRef("http://example.org/other"), EX_P, Literal("c"))])
    backend.remove((EX_S, None, None))
    result = backend.query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    assert len(result) == 1


def test_clear_default_graph_empties_it(backend):
    backend.add([(EX_S, EX_P, Literal("v"))])
    backend.clear()
    result = backend.query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    assert len(result) == 0


def test_named_graph_is_isolated_from_default(backend):
    backend.add([(EX_S, EX_P, Literal("default"))])
    backend.add([(EX_S, EX_P, Literal("named"))], graph=EX_G)

    in_named = backend.query(
        "CONSTRUCT { ?s ?p ?o } WHERE { "
        "GRAPH <http://example.org/g> { ?s ?p ?o } }"
    )
    assert (EX_S, EX_P, Literal("named")) in in_named
    assert (EX_S, EX_P, Literal("default")) not in in_named


def test_clear_named_graph_leaves_default_intact(backend):
    backend.add([(EX_S, EX_P, Literal("default"))])
    backend.add([(EX_S, EX_P, Literal("named"))], graph=EX_G)
    backend.clear(graph=EX_G)

    everything = backend.query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    assert (EX_S, EX_P, Literal("default")) in everything
    assert (EX_S, EX_P, Literal("named")) not in everything


def test_select_query_returns_bindings(backend):
    backend.add([(EX_S, EX_P, Literal("hello"))])
    rows = list(backend.query("SELECT ?o WHERE { ?s ?p ?o }"))
    assert len(rows) == 1
    assert str(rows[0][0]) == "hello"


def test_ask_query_returns_boolean(backend):
    backend.add([(EX_S, EX_P, Literal("v"))])
    result = backend.query("ASK { ?s ?p ?o }")
    assert bool(result) is True
