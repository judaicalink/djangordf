"""End-to-end mirror semantics for ``ObjectProperty(inverse=...)``.

Every test declares its own ``RDFModel`` subclasses with unique class
names so the metaclass-managed registry stays free of cross-test
contamination, and each test gets its own ``InMemoryBackend`` because
each subclass owns its own ``RDFManager`` (built lazily by the
metaclass on first access).
"""
import pytest
from rdflib import URIRef
from rdflib.namespace import SKOS


@pytest.fixture
def in_memory_backend(settings):
    settings.DJANGORDF_BACKEND = {
        "class": "djangordf.backends.memory.InMemoryBackend",
    }
    settings.DJANGORDF_DEFAULT_NAMESPACE = "http://example.org/d/"
    settings.DJANGORDF_DEFAULT_GRAPH = "http://example.org/g"


def _skos_term_model(name):
    """A pair of inverse `broader`/`narrower` properties on a single
    self-referential `RDFModel`."""
    from djangordf import LangStringProperty, ObjectProperty, RDFModel
    return type(
        name,
        (RDFModel,),
        {
            "pref_label": LangStringProperty(many=True),
            "broader": ObjectProperty("self", many=True, inverse="narrower"),
            "narrower": ObjectProperty("self", many=True, inverse="broader"),
        },
    )


def _construct_all(backend, graph_iri):
    return backend.query(
        "CONSTRUCT { ?s ?p ?o } WHERE { "
        f"GRAPH <{graph_iri}> {{ ?s ?p ?o }} }}"
    )


def test_save_writes_both_directions(in_memory_backend):
    Term = _skos_term_model("InvTermSaveBoth")
    parent = Term.objects.create()
    child = Term.objects.create(broader=[parent])

    g = _construct_all(child.objects.backend, Term._meta.graph_iri)
    assert (URIRef(child.iri), SKOS.broader, URIRef(parent.iri)) in g
    assert (URIRef(parent.iri), SKOS.narrower, URIRef(child.iri)) in g


def test_target_attribute_reads_mirror_after_save(in_memory_backend):
    Term = _skos_term_model("InvTermReadMirror")
    parent = Term.objects.create()
    child = Term.objects.create(broader=[parent])

    reloaded = Term.objects.get(parent.iri)
    assert [t.iri for t in reloaded.narrower] == [URIRef(child.iri)]


def test_update_strips_stale_mirror_on_previous_parent(in_memory_backend):
    Term = _skos_term_model("InvTermUpdate")
    parent_a = Term.objects.create()
    parent_b = Term.objects.create()
    child = Term.objects.create(broader=[parent_a])

    child.broader = [parent_b]
    child.save()

    g = _construct_all(child.objects.backend, Term._meta.graph_iri)
    assert (URIRef(parent_a.iri), SKOS.narrower, URIRef(child.iri)) not in g
    assert (URIRef(parent_b.iri), SKOS.narrower, URIRef(child.iri)) in g


def test_delete_strips_mirror_triples(in_memory_backend):
    Term = _skos_term_model("InvTermDelete")
    parent = Term.objects.create()
    child = Term.objects.create(broader=[parent])

    child.delete()

    g = _construct_all(child.objects.backend, Term._meta.graph_iri)
    assert (URIRef(parent.iri), SKOS.narrower, URIRef(child.iri)) not in g
    assert (URIRef(child.iri), SKOS.broader, URIRef(parent.iri)) not in g


def test_many_inverse_writes_each_parent(in_memory_backend):
    Term = _skos_term_model("InvTermManyParents")
    parent_a = Term.objects.create()
    parent_b = Term.objects.create()
    child = Term.objects.create(broader=[parent_a, parent_b])

    g = _construct_all(child.objects.backend, Term._meta.graph_iri)
    assert (URIRef(parent_a.iri), SKOS.narrower, URIRef(child.iri)) in g
    assert (URIRef(parent_b.iri), SKOS.narrower, URIRef(child.iri)) in g


def test_inverse_only_on_one_side_still_mirrors_writes(in_memory_backend):
    """The inverse direction needs only the forward side to declare
    ``inverse=``; the back-pointer property is optional for write
    mirroring (only required if you want to *read* it as a Python
    attribute via the manager). Here we leave it off and confirm the
    mirror triple still lands in the store."""
    from djangordf import ObjectProperty, RDFModel

    class InvOneSided(RDFModel):
        broader = ObjectProperty(
            "self",
            predicate=URIRef("http://example.org/one-broader"),
            inverse="back_pointer",
        )
        back_pointer = ObjectProperty(
            "self",
            predicate=URIRef("http://example.org/one-back"),
            many=True,
        )

    parent = InvOneSided.objects.create()
    child = InvOneSided.objects.create(broader=parent)

    g = _construct_all(child.objects.backend, InvOneSided._meta.graph_iri)
    assert (
        URIRef(parent.iri),
        URIRef("http://example.org/one-back"),
        URIRef(child.iri),
    ) in g
