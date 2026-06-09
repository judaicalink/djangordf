"""End-to-end behaviour for ``ObjectProperty(reverse=True)`` virtual
read-only properties. Each test declares its own ``RDFModel``
subclasses with unique class names so the metaclass-managed registry
stays free of cross-test contamination."""
import pytest
from rdflib import URIRef


@pytest.fixture
def in_memory_backend(settings):
    settings.DJANGORDF_BACKEND = {
        "class": "djangordf.backends.memory.InMemoryBackend",
    }
    settings.DJANGORDF_DEFAULT_NAMESPACE = "http://example.org/d/"
    settings.DJANGORDF_DEFAULT_GRAPH = "http://example.org/g"


def _author_book_models(suffix):
    """Author/Book pair where Author.books is a reverse property
    pointing at Book.author."""
    from djangordf import DataProperty, ObjectProperty, RDFModel

    Book = type(
        f"Book{suffix}",
        (RDFModel,),
        {
            "title": DataProperty(
                predicate=URIRef("http://example.org/title"),
            ),
            # Forward author link; lives on Book.
            "author": ObjectProperty(
                f"Author{suffix}",
                predicate=URIRef("http://example.org/author"),
            ),
        },
    )
    Author = type(
        f"Author{suffix}",
        (RDFModel,),
        {
            # Reverse view of Book.author.
            "books": ObjectProperty(
                Book,
                predicate=URIRef("http://example.org/author"),
                many=True,
                reverse=True,
            ),
        },
    )
    return Author, Book


def test_save_does_not_emit_triples_for_reverse_property(in_memory_backend):
    Author, Book = _author_book_models("Save")
    author = Author.objects.create()
    # Try setting the reverse attribute directly — must not break save.
    author.books = [Book(iri="http://example.org/d/dummy")]
    author.save()

    graph = author.objects.backend.query(
        "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH "
        f"<{Author._meta.graph_iri}> {{ ?s ?p ?o }} }}"
    )
    forward = list(graph.triples((
        URIRef(author.iri),
        URIRef("http://example.org/author"),
        None,
    )))
    assert forward == []


def test_get_hydrates_reverse_property_with_target_ghost_instances(in_memory_backend):
    Author, Book = _author_book_models("Hydrate")
    author = Author.objects.create()
    book1 = Book.objects.create(title="A", author=author)
    book2 = Book.objects.create(title="B", author=author)

    reloaded = Author.objects.get(author.iri)
    fetched_iris = sorted(str(b.iri) for b in reloaded.books)
    assert fetched_iris == sorted([str(book1.iri), str(book2.iri)])


def test_filter_terminal_reverse_segment_emits_swapped_pattern(in_memory_backend):
    Author, Book = _author_book_models("FilterTerm")
    author = Author.objects.create()
    other = Author.objects.create()
    target_book = Book.objects.create(title="Target", author=author)
    Book.objects.create(title="Sibling", author=author)
    Book.objects.create(title="UnrelatedBook", author=other)

    matches = list(Author.objects.filter(books=target_book))
    assert [m.iri for m in matches] == [URIRef(author.iri)]


def test_filter_non_terminal_reverse_then_forward(in_memory_backend):
    Author, Book = _author_book_models("FilterMid")
    author = Author.objects.create()
    other = Author.objects.create()
    Book.objects.create(title="Target Title", author=author)
    Book.objects.create(title="Other", author=other)

    matches = list(Author.objects.filter(books__title="Target Title"))
    assert [m.iri for m in matches] == [URIRef(author.iri)]


def test_filter_reverse_segment_with_suffix(in_memory_backend):
    Author, Book = _author_book_models("FilterSfx")
    author = Author.objects.create()
    other = Author.objects.create()
    Book.objects.create(title="The Book about cats", author=author)
    Book.objects.create(title="Boring", author=other)

    matches = list(Author.objects.filter(books__title__icontains="CATS"))
    assert [m.iri for m in matches] == [URIRef(author.iri)]


def test_reverse_property_does_not_inherit_skos_default_predicate(in_memory_backend):
    """A reverse property named like a SKOS convention must not get
    the SKOS predicate auto-assigned — it must carry an explicit
    predicate (or be left unconfigured)."""
    from djangordf import ObjectProperty, RDFModel

    class TermSkosRev(RDFModel):
        # ``broader`` would normally be auto-wired to skos:broader,
        # but reverse=True suppresses that.
        broader = ObjectProperty("self", reverse=True)

    assert TermSkosRev._properties["broader"].predicate is None
