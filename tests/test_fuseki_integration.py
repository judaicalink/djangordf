"""Integration tests for FusekiBackend against a real Fuseki instance.

These tests are marked with ``@pytest.mark.fuseki`` and are excluded by
the default pytest run (see ``pytest.ini``). To run them locally start
the bundled docker-compose Fuseki and call::

    docker compose up -d fuseki
    pytest -m fuseki
"""
import os

import pytest
from rdflib import Literal, URIRef


pytestmark = pytest.mark.fuseki


FUSEKI_ENDPOINT = os.environ.get(
    "DJANGORDF_FUSEKI_ENDPOINT", "http://localhost:3030/ds"
)


@pytest.fixture
def backend():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint=FUSEKI_ENDPOINT)
    backend.clear()
    yield backend
    backend.clear()


def test_roundtrip_against_real_fuseki(backend):
    s = URIRef("http://example.org/s")
    p = URIRef("http://example.org/p")
    o = Literal("hello")
    backend.add([(s, p, o)])
    result = backend.query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    assert (s, p, o) in result
