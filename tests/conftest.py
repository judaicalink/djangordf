"""Shared test fixtures and helpers for the djangordf suite."""
import pytest
from rdflib import Graph


def load_graph(path):
    """Load a Turtle file into a fresh rdflib Graph."""
    g = Graph()
    g.parse(path, format="turtle")
    return g


@pytest.fixture(autouse=True)
def reset_backend_between_tests():
    """Drop the process-wide cached backend so each test starts with a
    fresh in-memory store. Without this, the singleton cache in
    ``djangordf.conf`` would leak triples across tests."""
    from djangordf import conf
    conf.reset_backend()
    yield
    conf.reset_backend()


@pytest.fixture
def in_memory_backend(settings):
    """Documented opt-in for tests that want an isolated InMemoryBackend.

    Each ``RDFModel`` subclass declared inside a test gets its own
    manager (one per class definition) which lazy-instantiates a new
    backend from these settings, so isolation is naturally per-test
    when tests use unique class names. This fixture exists so tests
    can declare intent explicitly and survive any future tightening of
    the policy.
    """
    settings.DJANGORDF_BACKEND = {
        "class": "djangordf.backends.memory.InMemoryBackend",
    }
    settings.DJANGORDF_DEFAULT_NAMESPACE = "http://example.org/d/"
    settings.DJANGORDF_DEFAULT_GRAPH = "http://example.org/g"
