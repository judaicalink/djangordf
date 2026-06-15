"""Integration tests for FusekiBackend against a real Fuseki instance.

These tests are marked with ``@pytest.mark.fuseki`` and are excluded
by the default pytest run on developer machines (see ``pytest.ini``).
The CI workflow boots a Fuseki service container and runs them via
``pytest -m fuseki``. To run locally, start the bundled
``docker-compose.yml`` and point ``DJANGORDF_FUSEKI_ENDPOINT`` at it::

    docker compose up -d fuseki
    pytest -m fuseki
"""
import os

import pytest
from rdflib import Literal, URIRef
from rdflib.namespace import XSD


pytestmark = pytest.mark.fuseki


FUSEKI_ENDPOINT = os.environ.get(
    "DJANGORDF_FUSEKI_ENDPOINT", "http://localhost:3030/ds"
)
FUSEKI_USER = os.environ.get("DJANGORDF_FUSEKI_USER", "admin")
FUSEKI_PASSWORD = os.environ.get("DJANGORDF_FUSEKI_PASSWORD", "admin")


@pytest.fixture
def backend():
    """Yield a FusekiBackend pointed at the live instance, with every
    named graph wiped before and after the test."""
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(
        endpoint=FUSEKI_ENDPOINT,
        user=FUSEKI_USER,
        password=FUSEKI_PASSWORD,
    )
    backend.update("CLEAR ALL")
    yield backend
    backend.update("CLEAR ALL")


# -- backend method coverage ------------------------------------------------

def test_construct_query_returns_graph(backend):
    s = URIRef("http://example.org/s")
    p = URIRef("http://example.org/p")
    o = Literal("hello")
    backend.add([(s, p, o)])
    result = backend.query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    assert (s, p, o) in result


def test_select_query_returns_rows(backend):
    s = URIRef("http://example.org/s")
    p = URIRef("http://example.org/p")
    backend.add([(s, p, Literal("v"))])
    rows = list(backend.query("SELECT ?o WHERE { ?s ?p ?o }"))
    assert len(rows) == 1
    assert str(rows[0][0]) == "v"


def test_ask_query_returns_boolean(backend):
    s = URIRef("http://example.org/s")
    p = URIRef("http://example.org/p")
    backend.add([(s, p, Literal("v"))])
    result = backend.query("ASK { ?s ?p ?o }")
    assert bool(result) is True


def test_update_returns_response(backend):
    response = backend.update(
        'INSERT DATA { '
        '<http://example.org/s> <http://example.org/p> "v" }'
    )
    assert response is not None
    assert response.status_code in (200, 204)


def test_add_then_remove_with_subject_pattern(backend):
    s = URIRef("http://example.org/s")
    other = URIRef("http://example.org/other")
    p = URIRef("http://example.org/p")
    backend.add([(s, p, Literal("a"))])
    backend.add([(other, p, Literal("b"))])
    backend.remove((s, None, None))
    rows = list(backend.query("SELECT ?s WHERE { ?s ?p ?o }"))
    assert [str(row[0]) for row in rows] == [str(other)]


def test_named_graph_isolation(backend):
    s = URIRef("http://example.org/s")
    p = URIRef("http://example.org/p")
    g = URIRef("http://example.org/g")
    backend.add([(s, p, Literal("default"))])
    backend.add([(s, p, Literal("named"))], graph=g)
    in_named = backend.query(
        "CONSTRUCT { ?s ?p ?o } WHERE { "
        f"GRAPH <{g}> {{ ?s ?p ?o }} }}"
    )
    assert (s, p, Literal("named")) in in_named
    assert (s, p, Literal("default")) not in in_named


def test_clear_default_graph(backend):
    backend.add([(
        URIRef("http://example.org/x"),
        URIRef("http://example.org/p"),
        Literal("v"),
    )])
    backend.clear()
    result = backend.query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    assert len(result) == 0


def test_clear_named_graph_leaves_default_intact(backend):
    s = URIRef("http://example.org/s")
    p = URIRef("http://example.org/p")
    g = URIRef("http://example.org/g")
    backend.add([(s, p, Literal("default"))])
    backend.add([(s, p, Literal("named"))], graph=g)
    backend.clear(graph=g)
    rows = list(backend.query("SELECT ?o WHERE { ?s ?p ?o }"))
    assert [str(row[0]) for row in rows] == ["default"]


# -- end-to-end RDFModel roundtrip ------------------------------------------

def test_rdfmodel_roundtrip_against_live_fuseki(settings, backend):
    """A full create / get / delete cycle through `RDFManager` against
    a real Fuseki backend, mirroring the in-memory walking-skeleton
    acceptance script."""
    settings.DJANGORDF_BACKEND = {
        "class": "djangordf.backends.fuseki.FusekiBackend",
        "endpoint": FUSEKI_ENDPOINT,
        "user": FUSEKI_USER,
        "password": FUSEKI_PASSWORD,
    }
    settings.DJANGORDF_DEFAULT_NAMESPACE = "http://example.org/d/"
    settings.DJANGORDF_DEFAULT_GRAPH = "http://example.org/g"

    from djangordf import DataProperty, RDFModel, conf
    conf.reset_backend()

    class FusekiTerm(RDFModel):
        title = DataProperty(
            predicate=URIRef("http://example.org/title"),
            datatype=XSD.string,
        )

        class Meta:
            class_iri = "http://example.org/IntegrationTerm"
            graph_iri = "http://example.org/g"

    inst = FusekiTerm.objects.create(title="hello")
    fetched = FusekiTerm.objects.get(inst.iri)
    assert fetched.title == "hello"

    inst.delete()
    with pytest.raises(FusekiTerm.DoesNotExist):
        FusekiTerm.objects.get(inst.iri)
