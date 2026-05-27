"""Tests for djangordf.manager (minimal save/delete in this milestone)."""
from unittest import mock

from rdflib import URIRef


class _DummyModel:
    pass


def test_manager_holds_model_reference():
    from djangordf.manager import RDFManager
    m = RDFManager(_DummyModel)
    assert m.model_class is _DummyModel


def test_save_issues_delete_then_insert_via_backend():
    from djangordf.manager import RDFManager

    fake_backend = mock.Mock()

    class FakeModel:
        _meta = mock.Mock(
            graph_iri=URIRef("http://example.org/g"),
            class_iri=URIRef("http://example.org/C"),
        )

        def _to_triples(self):
            return [
                (
                    URIRef("http://example.org/s"),
                    URIRef("http://example.org/p"),
                    URIRef("http://example.org/o"),
                )
            ]

    instance = FakeModel()
    instance.iri = URIRef("http://example.org/s")

    m = RDFManager(FakeModel)
    m._backend = fake_backend
    m.save(instance)

    fake_backend.update.assert_called_once()
    sparql = fake_backend.update.call_args.args[0]
    assert "DELETE" in sparql
    assert "INSERT DATA" in sparql
    assert "<http://example.org/s>" in sparql
    assert "<http://example.org/g>" in sparql


def test_delete_removes_all_triples_for_iri_in_graph():
    from djangordf.manager import RDFManager

    fake_backend = mock.Mock()

    class FakeModel:
        _meta = mock.Mock(graph_iri=URIRef("http://example.org/g"))

    instance = FakeModel()
    instance.iri = URIRef("http://example.org/s")

    m = RDFManager(FakeModel)
    m._backend = fake_backend
    m.delete(instance)

    fake_backend.update.assert_called_once()
    sparql = fake_backend.update.call_args.args[0]
    assert "DELETE" in sparql
    assert "<http://example.org/s>" in sparql
    assert "<http://example.org/g>" in sparql
