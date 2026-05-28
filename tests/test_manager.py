"""Tests for djangordf.manager.

Two layers:

* mocked-backend unit tests pin down the exact SPARQL we emit;
* InMemoryBackend roundtrip tests exercise the full CRUD pipeline
  including hydration via ``prop.from_rdf``.
"""
from unittest import mock

import pytest
from rdflib import Literal, URIRef
from rdflib.namespace import SKOS, XSD


# -- mocked-backend tests ---------------------------------------------------

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


def test_queryset_is_lazy_no_backend_hit_until_iterated():
    from djangordf.manager import RDFManager, RDFQuerySet

    fake_backend = mock.Mock()

    class FakeModel:
        _meta = mock.Mock(
            graph_iri=URIRef("http://example.org/g"),
            class_iri=SKOS.Concept,
        )
        _properties = {}

    m = RDFManager(FakeModel)
    m._backend = fake_backend

    qs = m.all()
    assert isinstance(qs, RDFQuerySet)
    fake_backend.query.assert_not_called()


# -- InMemoryBackend roundtrip tests ----------------------------------------

@pytest.fixture
def fresh_backend(settings):
    """Configure the in-memory backend and per-model defaults. Each
    Term subclass declared inside a test owns its own manager, so the
    backend instance is naturally per-test (the manager builds it
    lazily on first access via ``conf.get_backend``)."""
    settings.DJANGORDF_BACKEND = {
        "class": "djangordf.backends.memory.InMemoryBackend",
    }
    settings.DJANGORDF_DEFAULT_NAMESPACE = "http://example.org/d/"
    settings.DJANGORDF_DEFAULT_GRAPH = "http://example.org/g"


def _term_model(name="Term"):
    """Build an isolated RDFModel subclass with a few properties."""
    from djangordf.models import RDFModel
    from djangordf.properties import DataProperty, ObjectProperty

    Term = type(
        name,
        (RDFModel,),
        {
            "title": DataProperty(
                predicate=URIRef("http://example.org/title"),
            ),
            "count": DataProperty(
                predicate=URIRef("http://example.org/count"),
                datatype=XSD.integer,
            ),
            "broader": ObjectProperty("self"),
        },
    )
    return Term


def test_create_persists_and_returns_instance(fresh_backend):
    Term = _term_model("TermCreate")
    inst = Term.objects.create(title="Hello")
    assert inst.iri is not None
    assert inst.title == "Hello"
    fetched = Term.objects.get(inst.iri)
    assert fetched.title == "Hello"


def test_get_roundtrips_every_property_value(fresh_backend):
    Term = _term_model("TermRoundtrip")
    inst = Term.objects.create(title="Alpha", count=42)
    fetched = Term.objects.get(inst.iri)
    assert fetched.title == "Alpha"
    assert fetched.count == 42


def test_get_raises_doesnotexist_for_missing_iri(fresh_backend):
    Term = _term_model("TermMissing")
    with pytest.raises(Term.DoesNotExist):
        Term.objects.get("http://example.org/d/nope")


def test_save_is_idempotent(fresh_backend):
    Term = _term_model("TermIdempotent")
    inst = Term.objects.create(title="X")
    iri = inst.iri

    backend = inst.objects.backend
    construct = (
        f"CONSTRUCT {{ <{iri}> ?p ?o }} "
        f"WHERE {{ GRAPH <{Term._meta.graph_iri}> "
        f"{{ <{iri}> ?p ?o }} }}"
    )

    triples_first = len(backend.query(construct))
    inst.save()
    triples_second = len(backend.query(construct))
    assert triples_first == triples_second


def test_save_overwrites_stale_triples(fresh_backend):
    Term = _term_model("TermUpdate")
    inst = Term.objects.create(title="Old")
    iri = inst.iri
    inst.title = "New"
    inst.save()
    fetched = Term.objects.get(iri)
    assert fetched.title == "New"


def test_delete_removes_all_triples(fresh_backend):
    Term = _term_model("TermDelete")
    inst = Term.objects.create(title="Goodbye")
    iri = inst.iri
    inst.delete()
    with pytest.raises(Term.DoesNotExist):
        Term.objects.get(iri)


def test_all_returns_every_instance(fresh_backend):
    Term = _term_model("TermAll")
    Term.objects.create(title="A")
    Term.objects.create(title="B")
    Term.objects.create(title="C")
    titles = sorted(t.title for t in Term.objects.all())
    assert titles == ["A", "B", "C"]


def test_filter_by_exact_value_returns_subset(fresh_backend):
    Term = _term_model("TermFilter")
    Term.objects.create(title="Match", count=1)
    Term.objects.create(title="Match", count=2)
    Term.objects.create(title="Other", count=3)

    matches = list(Term.objects.filter(title="Match"))
    assert len(matches) == 2
    assert {m.count for m in matches} == {1, 2}


def test_filter_unknown_attribute_raises(fresh_backend):
    Term = _term_model("TermFilterUnknown")
    with pytest.raises(ValueError):
        Term.objects.filter(nope="x")


def test_queryset_count_matches_len(fresh_backend):
    Term = _term_model("TermCount")
    Term.objects.create(title="A")
    Term.objects.create(title="B")
    qs = Term.objects.all()
    assert qs.count() == 2
    assert len(qs) == 2


def test_queryset_first_returns_none_when_empty(fresh_backend):
    Term = _term_model("TermFirstEmpty")
    qs = Term.objects.all()
    assert qs.first() is None


def test_queryset_first_returns_one_instance(fresh_backend):
    Term = _term_model("TermFirst")
    Term.objects.create(title="Only")
    qs = Term.objects.all()
    first = qs.first()
    assert first is not None
    assert first.title == "Only"


def test_filter_by_object_property_uses_iri(fresh_backend):
    Term = _term_model("TermObjFilter")
    parent = Term.objects.create(title="Parent")
    Term.objects.create(title="Child1", broader=parent)
    Term.objects.create(title="Child2", broader=parent)
    Term.objects.create(title="Lonely")

    children = list(Term.objects.filter(broader=parent))
    assert {c.title for c in children} == {"Child1", "Child2"}


def test_queryset_classes_are_importable_from_package_root():
    from djangordf import RDFManager, RDFQuerySet
    from djangordf.manager import (
        RDFManager as Mgr,
        RDFQuerySet as QS,
    )
    assert RDFManager is Mgr
    assert RDFQuerySet is QS


def test_get_hydrates_via_property_from_rdf(fresh_backend):
    """Use a literal whose Python form differs from string-of-itself to
    prove from_rdf is dispatched (not a naive str() coercion)."""
    Term = _term_model("TermHydrate")
    inst = Term.objects.create(title="X", count=7)
    fetched = Term.objects.get(inst.iri)
    assert isinstance(fetched.count, int)
    assert fetched.count == 7
    raw_objects = list(
        inst.objects.backend.query(
            "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH "
            f"<{Term._meta.graph_iri}> {{ ?s ?p ?o }} }}"
        ).objects(URIRef(inst.iri), URIRef("http://example.org/count"))
    )
    assert raw_objects == [Literal(7, datatype=XSD.integer)]
