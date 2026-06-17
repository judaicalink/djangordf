"""Tests pinning the N+1 collapse on ``RDFQuerySet``.

The contract: regardless of the number of matched subjects, the
queryset issues exactly two backend ``query`` calls — one
``SELECT DISTINCT ?s`` plus one bulk ``CONSTRUCT`` scoped by
``FILTER(?s IN (...))``. Models that declare reverse properties
issue a third query (one CONSTRUCT for reverse triples).
"""
import pytest
from rdflib import URIRef


@pytest.fixture
def in_memory_backend(settings):
    settings.DJANGORDF_BACKEND = {
        "class": "djangordf.backends.memory.InMemoryBackend",
    }
    settings.DJANGORDF_DEFAULT_NAMESPACE = "http://example.org/d/"
    settings.DJANGORDF_DEFAULT_GRAPH = "http://example.org/g"


def _query_count(backend):
    """Wrap ``backend.query`` so tests can assert how many SPARQL
    queries a queryset materialisation issues."""
    from unittest import mock
    spy = mock.Mock(wraps=backend.query)
    backend.query = spy  # type: ignore[assignment]
    return spy


def _basic_term_model(name):
    from djangordf import DataProperty, RDFModel
    return type(
        name,
        (RDFModel,),
        {
            "title": DataProperty(
                predicate=URIRef("http://example.org/title"),
            ),
        },
    )


def _term_with_reverse_models(suffix):
    from djangordf import DataProperty, ObjectProperty, RDFModel

    BookMeta = type(
        "Meta", (), {"class_iri": f"http://example.org/Book{suffix}"},
    )
    AuthorMeta = type(
        "Meta", (), {"class_iri": f"http://example.org/Author{suffix}"},
    )
    Book = type(
        f"NPlus1Book{suffix}",
        (RDFModel,),
        {
            "title": DataProperty(
                predicate=URIRef("http://example.org/title"),
            ),
            "author": ObjectProperty(
                f"NPlus1Author{suffix}",
                predicate=URIRef("http://example.org/author"),
            ),
            "Meta": BookMeta,
        },
    )
    Author = type(
        f"NPlus1Author{suffix}",
        (RDFModel,),
        {
            "books": ObjectProperty(
                Book,
                predicate=URIRef("http://example.org/author"),
                many=True,
                reverse=True,
            ),
            "Meta": AuthorMeta,
        },
    )
    return Author, Book


# -- query-count contracts -------------------------------------------------

def test_queryset_uses_two_queries_for_many_subjects(in_memory_backend):
    Term = _basic_term_model("NPlus1Many")
    for i in range(10):
        Term.objects.create(title=f"T{i}")
    spy = _query_count(Term.objects.backend)
    items = list(Term.objects.all())
    assert len(items) == 10
    assert spy.call_count == 2, (
        f"expected 2 queries (SELECT + bulk CONSTRUCT) for 10 subjects, "
        f"got {spy.call_count}"
    )


def test_queryset_uses_two_queries_for_single_subject(in_memory_backend):
    Term = _basic_term_model("NPlus1One")
    Term.objects.create(title="only")
    spy = _query_count(Term.objects.backend)
    items = list(Term.objects.all())
    assert len(items) == 1
    assert spy.call_count == 2


def test_queryset_uses_one_query_for_empty_result(in_memory_backend):
    Term = _basic_term_model("NPlus1Empty")
    spy = _query_count(Term.objects.backend)
    items = list(Term.objects.all())
    assert items == []
    assert spy.call_count == 1, (
        f"empty queryset should only issue the SELECT, got {spy.call_count}"
    )


def test_queryset_with_reverse_uses_three_queries(in_memory_backend):
    Author, Book = _term_with_reverse_models("Count")
    a1 = Author.objects.create()
    a2 = Author.objects.create()
    Book.objects.create(title="A", author=a1)
    Book.objects.create(title="B", author=a2)

    spy = _query_count(Author.objects.backend)
    list(Author.objects.all())
    assert spy.call_count == 3, (
        f"queryset over a model with reverse properties should issue "
        f"SELECT + forward CONSTRUCT + reverse CONSTRUCT (3 queries); "
        f"got {spy.call_count}"
    )


# -- behaviour parity ------------------------------------------------------

def test_bulk_hydration_preserves_ordering(in_memory_backend):
    from rdflib.namespace import XSD
    from djangordf import DataProperty, RDFModel

    Term = type(
        "NPlus1Order",
        (RDFModel,),
        {
            "rank": DataProperty(
                predicate=URIRef("http://example.org/rank"),
                datatype=XSD.integer,
            ),
        },
    )
    Term.objects.create(rank=3)
    Term.objects.create(rank=1)
    Term.objects.create(rank=2)
    items = list(Term.objects.all().order_by("rank"))
    assert [t.rank for t in items] == [1, 2, 3]


def test_bulk_hydration_keeps_property_values(in_memory_backend):
    Term = _basic_term_model("NPlus1Hyd")
    Term.objects.create(title="Alpha")
    Term.objects.create(title="Beta")
    Term.objects.create(title="Gamma")
    titles = sorted(t.title for t in Term.objects.all())
    assert titles == ["Alpha", "Beta", "Gamma"]


def test_bulk_hydration_reverse_property_round_trip(in_memory_backend):
    Author, Book = _term_with_reverse_models("Hyd")
    author = Author.objects.create()
    Book.objects.create(title="A", author=author)
    Book.objects.create(title="B", author=author)

    reloaded = list(Author.objects.all())
    assert len(reloaded) == 1
    book_iris = sorted(str(b.iri) for b in reloaded[0].books)
    assert len(book_iris) == 2


def test_filter_with_lookup_suffix_still_collapses(in_memory_backend):
    Term = _basic_term_model("NPlus1Sfx")
    for word in ("cats", "Cats", "dogs"):
        Term.objects.create(title=word)
    spy = _query_count(Term.objects.backend)
    items = list(Term.objects.filter(title__icontains="cat"))
    assert sorted(t.title for t in items) == ["Cats", "cats"]
    # SELECT + bulk CONSTRUCT regardless of the filter.
    assert spy.call_count == 2


def test_get_single_instance_still_uses_one_query(in_memory_backend):
    """`manager.get(iri)` keeps its original path: one CONSTRUCT for
    forward triples (and one more for reverse-bearing models)."""
    Term = _basic_term_model("NPlus1Get")
    inst = Term.objects.create(title="x")
    spy = _query_count(Term.objects.backend)
    Term.objects.get(inst.iri)
    assert spy.call_count == 1


def test_first_uses_two_queries(in_memory_backend):
    Term = _basic_term_model("NPlus1First")
    Term.objects.create(title="a")
    Term.objects.create(title="b")
    spy = _query_count(Term.objects.backend)
    assert Term.objects.all().order_by("title").first().title == "a"
    assert spy.call_count == 2
