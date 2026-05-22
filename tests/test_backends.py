"""Tests for djangordf.backends."""
import pytest


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
