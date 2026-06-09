"""End-to-end behaviour for ``Q`` filter composition."""
import pytest
from rdflib import URIRef
from rdflib.namespace import XSD


@pytest.fixture
def in_memory_backend(settings):
    settings.DJANGORDF_BACKEND = {
        "class": "djangordf.backends.memory.InMemoryBackend",
    }
    settings.DJANGORDF_DEFAULT_NAMESPACE = "http://example.org/d/"
    settings.DJANGORDF_DEFAULT_GRAPH = "http://example.org/g"


def _q_term_model(name="QTerm"):
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


# -- Q class behaviour ------------------------------------------------------

def test_q_empty_raises_value_error():
    from djangordf import Q
    with pytest.raises(ValueError):
        Q()


def test_q_bool_raises_type_error():
    from djangordf import Q
    with pytest.raises(TypeError):
        bool(Q(title="x"))


def test_q_or_returns_q_with_or_connector():
    from djangordf import Q
    q = Q(a=1) | Q(b=2)
    assert q.connector == Q.OR


def test_q_and_flattens_same_connector_chains():
    from djangordf import Q
    q = Q(a=1) & Q(b=2) & Q(c=3)
    assert q.connector == Q.AND
    assert len(q.children) == 3


def test_q_invert_flips_negation():
    from djangordf import Q
    q = Q(a=1)
    inverted = ~q
    assert inverted.negated is True
    assert q.negated is False


# -- filter() with Q --------------------------------------------------------

def test_q_or_returns_union_subset(in_memory_backend):
    from djangordf import Q
    Term = _q_term_model("QTermOr")
    Term.objects.create(title="A")
    Term.objects.create(title="B")
    Term.objects.create(title="C")
    matches = sorted(
        t.title for t in Term.objects.filter(Q(title="A") | Q(title="B"))
    )
    assert matches == ["A", "B"]


def test_q_and_is_equivalent_to_kwargs(in_memory_backend):
    from djangordf import Q
    Term = _q_term_model("QTermAnd")
    Term.objects.create(title="Match", count=5)
    Term.objects.create(title="Match", count=99)
    Term.objects.create(title="NoMatch", count=5)

    via_q = sorted(
        t.count for t in Term.objects.filter(Q(title="Match") & Q(count=5))
    )
    via_kwargs = sorted(
        t.count for t in Term.objects.filter(title="Match", count=5)
    )
    assert via_q == via_kwargs == [5]


def test_q_not_returns_complement_within_class(in_memory_backend):
    from djangordf import Q
    Term = _q_term_model("QTermNot")
    Term.objects.create(title="keep")
    Term.objects.create(title="bad")
    Term.objects.create(title="alsokeep")
    matches = sorted(
        t.title for t in Term.objects.filter(~Q(title="bad"))
    )
    assert matches == ["alsokeep", "keep"]


def test_q_mixed_positional_and_kwargs_combine_with_and(in_memory_backend):
    from djangordf import Q
    Term = _q_term_model("QTermMix")
    Term.objects.create(title="A", count=10)
    Term.objects.create(title="B", count=10)
    Term.objects.create(title="A", count=1)
    matches = sorted(
        t.count for t in Term.objects.filter(
            Q(title="A") | Q(title="B"),
            count=10,
        )
    )
    assert matches == [10, 10]


def test_q_nested_or_and_combinations(in_memory_backend):
    from djangordf import Q
    Term = _q_term_model("QTermNested")
    Term.objects.create(title="A", count=1)
    Term.objects.create(title="B", count=99)
    Term.objects.create(title="C", count=99)
    Term.objects.create(title="D", count=1)
    # (title in {A,B}) AND (count != 1)
    matches = sorted(
        t.title for t in Term.objects.filter(
            (Q(title="A") | Q(title="B")) & ~Q(count=1)
        )
    )
    assert matches == ["B"]


def test_q_supports_lookup_suffixes(in_memory_backend):
    from djangordf import Q
    Term = _q_term_model("QTermSfx")
    Term.objects.create(title="cats", count=1)
    Term.objects.create(title="dogs", count=10)
    Term.objects.create(title="birds", count=5)
    matches = sorted(
        t.title for t in Term.objects.filter(
            Q(title__icontains="cat") | Q(count__gt=5)
        )
    )
    assert matches == ["cats", "dogs"]


def test_q_supports_cross_class_spans(in_memory_backend):
    from djangordf import Q
    Term = _q_term_model("QTermSpan")
    parent = Term.objects.create(title="Parent")
    Term.objects.create(title="Child1", broader=[parent])
    Term.objects.create(title="Child2", broader=[parent])
    Term.objects.create(title="Lonely")
    matches = sorted(
        t.title for t in Term.objects.filter(
            Q(broader__title="Parent") | Q(title="Lonely")
        )
    )
    assert matches == ["Child1", "Child2", "Lonely"]


def test_q_supports_reverse_segments(in_memory_backend):
    """Q composition must work for reverse-property paths too."""
    from djangordf import (
        DataProperty,
        ObjectProperty,
        Q,
        RDFModel,
    )

    Book = type(
        "QBook",
        (RDFModel,),
        {
            "title": DataProperty(
                predicate=URIRef("http://example.org/title"),
            ),
            "author": ObjectProperty(
                "QAuthor",
                predicate=URIRef("http://example.org/author"),
            ),
        },
    )
    Author = type(
        "QAuthor",
        (RDFModel,),
        {
            "name": DataProperty(
                predicate=URIRef("http://example.org/name"),
            ),
            "books": ObjectProperty(
                Book,
                predicate=URIRef("http://example.org/author"),
                many=True,
                reverse=True,
            ),
        },
    )

    a1 = Author.objects.create(name="A1")
    a2 = Author.objects.create(name="A2")
    Author.objects.create(name="Lonely")
    Book.objects.create(title="Catnip", author=a1)
    Book.objects.create(title="Plain", author=a2)

    matches = sorted(
        a.name for a in Author.objects.filter(
            Q(books__title__icontains="cat") | Q(name="Lonely")
        )
    )
    assert matches == ["A1", "Lonely"]


def test_flat_filter_still_emits_no_union(in_memory_backend):
    """Regression: simple `filter(a=..., b=...)` must produce SPARQL
    without UNION or FILTER NOT EXISTS so the old fast path stays
    byte-equivalent at the SPARQL level."""
    Term = _q_term_model("QTermFlat")
    qs = Term.objects.filter(title="X", count=1)
    sparql = qs._build_subject_sparql()
    assert "UNION" not in sparql
    assert "FILTER NOT EXISTS" not in sparql
