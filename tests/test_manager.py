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
        list(Term.objects.filter(nope="x"))


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


# -- cross-class lookups (filter spanning __) -------------------------------

def _lookup_term_model(name="LookupTerm"):
    """Term model used by the cross-class lookup tests."""
    from djangordf import (
        DataProperty,
        LangStringProperty,
        ObjectProperty,
        RDFModel,
    )

    Term = type(
        name,
        (RDFModel,),
        {
            "title": DataProperty(
                predicate=URIRef("http://example.org/title"),
            ),
            "pref_label": LangStringProperty(many=True),
            "broader": ObjectProperty("self", many=True),
        },
    )
    return Term


def test_filter_spans_one_objectproperty_to_dataproperty(fresh_backend):
    Term = _lookup_term_model("LookupSpan1")
    parent = Term.objects.create(title="Parent")
    Term.objects.create(title="Child1", broader=[parent])
    Term.objects.create(title="Child2", broader=[parent])
    Term.objects.create(title="Lonely")

    children = list(Term.objects.filter(broader__title="Parent"))
    assert {c.title for c in children} == {"Child1", "Child2"}


def test_filter_spans_one_objectproperty_to_langstring(fresh_backend):
    from djangordf.namespaces import LangString

    Term = _lookup_term_model("LookupSpanLang")
    parent = Term.objects.create(
        pref_label=[LangString("Buch", "de")],
    )
    Term.objects.create(title="ChildOfBuch", broader=[parent])
    Term.objects.create(title="UnrelatedChild")

    matches = list(
        Term.objects.filter(broader__pref_label=LangString("Buch", "de"))
    )
    assert [m.title for m in matches] == ["ChildOfBuch"]


def test_filter_spans_two_objectproperty_hops(fresh_backend):
    Term = _lookup_term_model("LookupSpan2")
    grand = Term.objects.create(title="Grand")
    parent = Term.objects.create(title="Parent", broader=[grand])
    Term.objects.create(title="Grandchild", broader=[parent])
    Term.objects.create(title="OrphanChild")

    matches = list(Term.objects.filter(broader__broader__title="Grand"))
    assert [m.title for m in matches] == ["Grandchild"]


def test_filter_combines_simple_and_spanning_kwargs(fresh_backend):
    Term = _lookup_term_model("LookupSpanCombo")
    parent_a = Term.objects.create(title="A")
    parent_b = Term.objects.create(title="B")
    Term.objects.create(title="ChildOfA1", broader=[parent_a])
    Term.objects.create(title="ChildOfA2", broader=[parent_a])
    Term.objects.create(title="ChildOfB", broader=[parent_b])

    matches = list(
        Term.objects.filter(broader__title="A", title="ChildOfA1")
    )
    assert [m.title for m in matches] == ["ChildOfA1"]


def test_filter_unknown_segment_on_path_raises(fresh_backend):
    Term = _lookup_term_model("LookupBadSegment")
    with pytest.raises(ValueError):
        list(Term.objects.filter(broader__no_such_attr="x"))


def test_filter_nonterminal_segment_must_be_objectproperty(fresh_backend):
    """`title` is a DataProperty; using it as a non-terminal hop must fail."""
    Term = _lookup_term_model("LookupNonTerm")
    with pytest.raises(ValueError):
        list(Term.objects.filter(title__broader="x"))


def test_filter_simple_single_segment_still_works(fresh_backend):
    """Single-segment filter behaviour must not regress."""
    Term = _lookup_term_model("LookupSimple")
    Term.objects.create(title="A")
    Term.objects.create(title="B")

    matches = list(Term.objects.filter(title="A"))
    assert [m.title for m in matches] == ["A"]


def test_filter_first_segment_must_exist_on_model(fresh_backend):
    Term = _lookup_term_model("LookupBadFirst")
    with pytest.raises(ValueError):
        list(Term.objects.filter(no_such_attr__title="x"))


# -- lookup suffixes --------------------------------------------------------

def _suffix_term_model(name):
    """Term used by the lookup-suffix tests: string title plus an
    integer count predicate so we can exercise numeric comparisons."""
    from djangordf import DataProperty, ObjectProperty, RDFModel

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
            "broader": ObjectProperty("self", many=True),
        },
    )
    return Term


def test_filter_iexact_matches_case_insensitively(fresh_backend):
    Term = _suffix_term_model("SfxIexact")
    Term.objects.create(title="Buch")
    Term.objects.create(title="buch")
    Term.objects.create(title="other")
    matches = sorted(t.title for t in Term.objects.filter(title__iexact="BUCH"))
    assert matches == ["Buch", "buch"]


def test_filter_contains_substring(fresh_backend):
    Term = _suffix_term_model("SfxContains")
    Term.objects.create(title="Roman")
    Term.objects.create(title="Romance")
    Term.objects.create(title="Buch")
    matches = sorted(t.title for t in Term.objects.filter(title__contains="Rom"))
    assert matches == ["Roman", "Romance"]


def test_filter_icontains_substring_case_insensitive(fresh_backend):
    Term = _suffix_term_model("SfxIContains")
    Term.objects.create(title="Roman")
    Term.objects.create(title="romance")
    Term.objects.create(title="Buch")
    matches = sorted(t.title for t in Term.objects.filter(title__icontains="ROM"))
    assert matches == ["Roman", "romance"]


def test_filter_startswith_and_istartswith(fresh_backend):
    Term = _suffix_term_model("SfxStarts")
    Term.objects.create(title="Buch")
    Term.objects.create(title="buchstabe")
    Term.objects.create(title="Other")
    starts = sorted(t.title for t in Term.objects.filter(title__startswith="Buch"))
    istarts = sorted(t.title for t in Term.objects.filter(title__istartswith="BUCH"))
    assert starts == ["Buch"]
    assert istarts == ["Buch", "buchstabe"]


def test_filter_endswith_and_iendswith(fresh_backend):
    Term = _suffix_term_model("SfxEnds")
    Term.objects.create(title="Hand-Buch")
    Term.objects.create(title="StadtBUCH")
    Term.objects.create(title="Other")
    ends = sorted(t.title for t in Term.objects.filter(title__endswith="Buch"))
    iends = sorted(t.title for t in Term.objects.filter(title__iendswith="buch"))
    assert ends == ["Hand-Buch"]
    assert iends == ["Hand-Buch", "StadtBUCH"]


def test_filter_in_membership_strings(fresh_backend):
    Term = _suffix_term_model("SfxInStr")
    Term.objects.create(title="A")
    Term.objects.create(title="B")
    Term.objects.create(title="C")
    matches = sorted(t.title for t in Term.objects.filter(title__in=["A", "C"]))
    assert matches == ["A", "C"]


def test_filter_in_membership_integers(fresh_backend):
    Term = _suffix_term_model("SfxInInt")
    Term.objects.create(count=1)
    Term.objects.create(count=2)
    Term.objects.create(count=3)
    matches = sorted(t.count for t in Term.objects.filter(count__in=[1, 3]))
    assert matches == [1, 3]


def test_filter_gt_gte_lt_lte_numeric(fresh_backend):
    Term = _suffix_term_model("SfxNumeric")
    Term.objects.create(count=1)
    Term.objects.create(count=5)
    Term.objects.create(count=10)
    assert sorted(t.count for t in Term.objects.filter(count__gt=4)) == [5, 10]
    assert sorted(t.count for t in Term.objects.filter(count__gte=5)) == [5, 10]
    assert sorted(t.count for t in Term.objects.filter(count__lt=10)) == [1, 5]
    assert sorted(t.count for t in Term.objects.filter(count__lte=5)) == [1, 5]


def test_filter_suffix_composes_with_cross_class_span(fresh_backend):
    Term = _suffix_term_model("SfxCompose")
    parent = Term.objects.create(title="Parent of Books")
    Term.objects.create(title="ChildA", broader=[parent])
    other = Term.objects.create(title="Other Parent")
    Term.objects.create(title="ChildB", broader=[other])
    matches = sorted(
        t.title for t in Term.objects.filter(broader__title__icontains="books")
    )
    assert matches == ["ChildA"]


def test_filter_property_named_like_a_suffix_not_peeled(fresh_backend):
    """A model with an attribute literally called ``exact`` must not
    have its name stolen by the suffix peeler."""
    from djangordf import DataProperty, RDFModel

    class TermWithExactAttr(RDFModel):
        exact = DataProperty(
            predicate=URIRef("http://example.org/exact"),
        )

    TermWithExactAttr.objects.create(exact="hit")
    TermWithExactAttr.objects.create(exact="miss")
    matches = [t.exact for t in TermWithExactAttr.objects.filter(exact="hit")]
    assert matches == ["hit"]


def test_filter_in_with_non_iterable_raises(fresh_backend):
    Term = _suffix_term_model("SfxInNonIter")
    with pytest.raises(TypeError):
        list(Term.objects.filter(count__in=42))
