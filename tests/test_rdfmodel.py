"""The twelve walking-skeleton acceptance tests from spec §9.

Each test declares its own ``RDFModel`` subclass with a unique class
name so the metaclass-managed model registry stays free of cross-test
contamination, and each test gets a fresh ``RDFManager`` (and thus a
fresh ``InMemoryBackend``) per the metaclass lazy-init contract.
"""
import pytest
from rdflib import Literal, URIRef
from rdflib.namespace import FOAF, RDF, SKOS, XSD


# 1
def test_create_mints_iri(in_memory_backend):
    from djangordf import LangStringProperty, RDFModel
    from djangordf.namespaces import LangString

    class Term1(RDFModel):
        pref_label = LangStringProperty(many=True)

    inst = Term1.objects.create(pref_label=[LangString("Buch", "de")])
    assert inst.iri is not None
    assert str(inst.iri).startswith("http://example.org/d/")


# 2
def test_save_writes_rdf_type_triple(in_memory_backend):
    from djangordf import LangStringProperty, RDFModel
    from djangordf.namespaces import LangString

    class Term2(RDFModel):
        pref_label = LangStringProperty(many=True)

    inst = Term2.objects.create(pref_label=[LangString("X", "en")])
    sparql = (
        "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH "
        f"<{Term2._meta.graph_iri}> {{ ?s ?p ?o }} }}"
    )
    g = inst.objects.backend.query(sparql)
    assert (URIRef(inst.iri), RDF.type, SKOS.Concept) in g


# 3
def test_save_writes_all_properties(in_memory_backend):
    from djangordf import DataProperty, LangStringProperty, RDFModel
    from djangordf.namespaces import LangString

    class Term3(RDFModel):
        pref_label = LangStringProperty()
        count = DataProperty(
            predicate=URIRef("http://example.org/count"),
            datatype=XSD.integer,
        )

    inst = Term3.objects.create(
        pref_label=LangString("Eins", "de"),
        count=1,
    )
    sparql = (
        "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH "
        f"<{Term3._meta.graph_iri}> {{ ?s ?p ?o }} }}"
    )
    g = inst.objects.backend.query(sparql)
    assert (URIRef(inst.iri), SKOS.prefLabel, Literal("Eins", lang="de")) in g
    assert (
        URIRef(inst.iri),
        URIRef("http://example.org/count"),
        Literal(1, datatype=XSD.integer),
    ) in g


# 4
def test_skos_default_predicate_for_pref_label(in_memory_backend):
    from djangordf import LangStringProperty, RDFModel

    class Term4(RDFModel):
        pref_label = LangStringProperty(many=True)

    assert Term4._properties["pref_label"].predicate == SKOS.prefLabel


# 5
def test_curie_class_iri_resolves(in_memory_backend):
    from djangordf import RDFModel

    class Person5(RDFModel):
        class Meta:
            class_iri = "foaf:Person"

    assert Person5._meta.class_iri == FOAF.Person


# 6
def test_get_round_trip(in_memory_backend):
    from djangordf import DataProperty, LangStringProperty, RDFModel
    from djangordf.namespaces import LangString

    class Term6(RDFModel):
        pref_label = LangStringProperty()
        count = DataProperty(
            predicate=URIRef("http://example.org/count"),
            datatype=XSD.integer,
        )

    inst = Term6.objects.create(
        pref_label=LangString("Sechs", "de"),
        count=6,
    )
    fetched = Term6.objects.get(inst.iri)
    assert fetched.pref_label == LangString("Sechs", "de")
    assert fetched.count == 6


# 7
def test_save_is_idempotent(in_memory_backend):
    from djangordf import DataProperty, RDFModel

    class Term7(RDFModel):
        title = DataProperty(predicate=URIRef("http://example.org/title"))

    inst = Term7.objects.create(title="x")
    sparql = (
        f"CONSTRUCT {{ <{inst.iri}> ?p ?o }} WHERE {{ GRAPH "
        f"<{Term7._meta.graph_iri}> {{ <{inst.iri}> ?p ?o }} }}"
    )
    first = len(inst.objects.backend.query(sparql))
    inst.save()
    second = len(inst.objects.backend.query(sparql))
    assert first == second


# 8
def test_update_overwrites_stale_triples(in_memory_backend):
    from djangordf import DataProperty, RDFModel

    class Term8(RDFModel):
        title = DataProperty(predicate=URIRef("http://example.org/title"))

    inst = Term8.objects.create(title="old")
    inst.title = "new"
    inst.save()
    fetched = Term8.objects.get(inst.iri)
    assert fetched.title == "new"


# 9
def test_delete_removes_all_triples(in_memory_backend):
    from djangordf import DataProperty, RDFModel

    class Term9(RDFModel):
        title = DataProperty(predicate=URIRef("http://example.org/title"))

    inst = Term9.objects.create(title="bye")
    iri = inst.iri
    inst.delete()
    sparql = (
        f"CONSTRUCT {{ <{iri}> ?p ?o }} WHERE {{ GRAPH "
        f"<{Term9._meta.graph_iri}> {{ <{iri}> ?p ?o }} }}"
    )
    assert len(inst.objects.backend.query(sparql)) == 0


# 10
def test_lang_string_round_trip(in_memory_backend):
    from djangordf import LangStringProperty, RDFModel
    from djangordf.namespaces import LangString

    class Term10(RDFModel):
        pref_label = LangStringProperty(many=True)

    inst = Term10.objects.create(
        pref_label=[LangString("Buch", "de"), LangString("Book", "en")],
    )
    fetched = Term10.objects.get(inst.iri)
    assert LangString("Buch", "de") in fetched.pref_label
    assert LangString("Book", "en") in fetched.pref_label


# 11
def test_object_property_self_reference(in_memory_backend):
    from djangordf import LangStringProperty, ObjectProperty, RDFModel
    from djangordf.namespaces import LangString

    class Term11(RDFModel):
        pref_label = LangStringProperty(many=True)
        broader = ObjectProperty("self", many=True)

    parent = Term11.objects.create(
        pref_label=[LangString("Parent", "en")],
    )
    child = Term11.objects.create(
        pref_label=[LangString("Child", "en")],
        broader=[parent],
    )
    fetched = Term11.objects.get(child.iri)
    assert len(fetched.broader) == 1
    assert fetched.broader[0].iri == parent.iri


# 12
def test_get_missing_iri_raises_does_not_exist(in_memory_backend):
    from djangordf import RDFModel

    class Term12(RDFModel):
        pass

    with pytest.raises(Term12.DoesNotExist):
        Term12.objects.get("http://example.org/d/never-existed")
