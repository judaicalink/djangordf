"""Tests for djangordf.models (RDFModel + RDFModelMeta)."""
from rdflib import URIRef
from rdflib.namespace import SKOS

from djangordf.properties import Property


# -- metaclass collection ---------------------------------------------------


def test_metaclass_collects_properties():
    from djangordf.models import RDFModel

    class Term(RDFModel):
        title = Property(predicate=URIRef("http://example.org/title"))

    assert "title" in Term._properties
    assert isinstance(Term._properties["title"], Property)
    assert Term._properties["title"].attr_name == "title"


def test_metaclass_does_not_collect_non_property_attributes():
    from djangordf.models import RDFModel

    class Term(RDFModel):
        title = Property()
        not_a_property = "just a string"

    assert "title" in Term._properties
    assert "not_a_property" not in Term._properties


# -- _build_meta defaults ---------------------------------------------------


def test_default_class_iri_is_skos_concept():
    from djangordf.models import RDFModel

    class Term(RDFModel):
        pass

    assert Term._meta.class_iri == SKOS.Concept


def test_meta_namespace_falls_back_to_urn_default(settings):
    if hasattr(settings, "DJANGORDF_DEFAULT_NAMESPACE"):
        del settings.DJANGORDF_DEFAULT_NAMESPACE
    from djangordf.models import RDFModel

    class TermFallback(RDFModel):
        pass

    assert str(TermFallback._meta.namespace).startswith(
        "urn:djangordf:termfallback:"
    )


def test_meta_namespace_comes_from_setting_when_present(settings):
    settings.DJANGORDF_DEFAULT_NAMESPACE = "http://judaicalink.org/data/"
    from djangordf.models import RDFModel

    class TermFromSettings(RDFModel):
        pass

    assert (
        str(TermFromSettings._meta.namespace)
        == "http://judaicalink.org/data/"
    )


def test_meta_graph_iri_falls_back_to_sentinel(settings):
    if hasattr(settings, "DJANGORDF_DEFAULT_GRAPH"):
        del settings.DJANGORDF_DEFAULT_GRAPH
    from djangordf.models import RDFModel

    class TermGraphFallback(RDFModel):
        pass

    assert str(TermGraphFallback._meta.graph_iri) == "urn:djangordf:default"


def test_meta_class_iri_resolves_curie_strings():
    from djangordf.models import RDFModel

    class TermCurie(RDFModel):
        class Meta:
            class_iri = "skos:Concept"

    assert TermCurie._meta.class_iri == SKOS.Concept


def test_meta_explicit_namespace_and_graph_override_settings():
    from djangordf.models import RDFModel

    class TermExplicit(RDFModel):
        class Meta:
            namespace = "http://judaicalink.org/explicit/"
            graph_iri = "http://judaicalink.org/graph/explicit"

    assert (
        str(TermExplicit._meta.namespace)
        == "http://judaicalink.org/explicit/"
    )
    assert (
        str(TermExplicit._meta.graph_iri)
        == "http://judaicalink.org/graph/explicit"
    )


# -- model registry ---------------------------------------------------------


def test_subclasses_registered_under_their_name():
    from djangordf.models import RDFModel, get_registered_model

    class TermRegistered(RDFModel):
        pass

    assert get_registered_model("TermRegistered") is TermRegistered


# -- identity and DoesNotExist ----------------------------------------------


def test_instance_starts_without_iri():
    from djangordf.models import RDFModel

    class TermNoIri(RDFModel):
        pass

    assert TermNoIri().iri is None


def test_explicit_iri_is_kept_as_urirf():
    from djangordf.models import RDFModel

    class TermExplicitIri(RDFModel):
        pass

    inst = TermExplicitIri(iri="http://example.org/t1")
    assert isinstance(inst.iri, URIRef)
    assert str(inst.iri) == "http://example.org/t1"


def test_instances_compare_equal_by_iri():
    from djangordf.models import RDFModel

    class TermEq(RDFModel):
        pass

    a = TermEq(iri="http://example.org/x")
    b = TermEq(iri="http://example.org/x")
    c = TermEq(iri="http://example.org/y")
    assert a == b
    assert a != c


def test_instances_without_iri_only_equal_themselves():
    from djangordf.models import RDFModel

    class TermNoIriEq(RDFModel):
        pass

    a = TermNoIriEq()
    b = TermNoIriEq()
    assert a != b
    assert a == a


def test_each_subclass_has_its_own_does_not_exist():
    from djangordf.models import RDFModel

    class TermDneA(RDFModel):
        pass

    class TermDneB(RDFModel):
        pass

    assert TermDneA.DoesNotExist is not TermDneB.DoesNotExist
    assert issubclass(TermDneA.DoesNotExist, Exception)
    assert issubclass(TermDneB.DoesNotExist, Exception)


# -- save / delete round-trip via InMemoryBackend ---------------------------


def test_save_mints_iri_in_configured_namespace(settings):
    settings.DJANGORDF_DEFAULT_NAMESPACE = "http://judaicalink.org/data/"
    from djangordf.models import RDFModel

    class TermSaveIri(RDFModel):
        title = Property(predicate=URIRef("http://example.org/title"))

    inst = TermSaveIri()
    inst.title = "hello"
    inst.save()
    assert str(inst.iri).startswith("http://judaicalink.org/data/")


def test_save_writes_rdf_type_triple_into_configured_graph(settings):
    settings.DJANGORDF_DEFAULT_NAMESPACE = "http://example.org/d/"
    settings.DJANGORDF_DEFAULT_GRAPH = "http://example.org/g"
    settings.DJANGORDF_BACKEND = {
        "class": "djangordf.backends.memory.InMemoryBackend",
    }
    from djangordf.models import RDFModel

    class TermSaveType(RDFModel):
        title = Property(predicate=URIRef("http://example.org/title"))

    inst = TermSaveType()
    inst.title = "hello"
    inst.save()

    backend = inst.objects.backend
    sparql = (
        "CONSTRUCT { ?s ?p ?o } WHERE { "
        f"GRAPH <{TermSaveType._meta.graph_iri}> {{ ?s ?p ?o }} "
        "}"
    )
    g = backend.query(sparql)
    from rdflib.namespace import RDF
    assert (URIRef(inst.iri), RDF.type, SKOS.Concept) in g


def test_to_triples_delegates_to_property_to_rdf():
    """The RDFModel._to_triples path must dispatch through each
    property's ``to_rdf``. Proven by installing a sentinel ``Property``
    subclass whose ``to_rdf`` returns a recognisable marker; the
    inline code path from #6 would have ignored the override and
    serialised the value as a plain Literal."""
    from djangordf.models import RDFModel
    from djangordf.properties import Property

    sentinel = URIRef("http://example.org/SENTINEL")

    class SentinelProperty(Property):
        def to_rdf(self, subject, value):
            return [(subject, self.predicate, sentinel)]

    class WithSentinel(RDFModel):
        weird = SentinelProperty(
            predicate=URIRef("http://example.org/w"),
        )

    inst = WithSentinel(iri="http://example.org/x")
    inst.weird = "ignored-by-sentinel"
    triples = inst._to_triples()
    assert (
        URIRef("http://example.org/x"),
        URIRef("http://example.org/w"),
        sentinel,
    ) in triples


def test_rdfmodel_is_importable_from_package_root():
    from djangordf import RDFModel as TopLevelModel
    from djangordf.models import RDFModel as ModuleModel
    assert TopLevelModel is ModuleModel


def test_property_is_importable_from_package_root():
    from djangordf import Property as TopLevelProperty
    from djangordf.properties import Property as ModuleProperty
    assert TopLevelProperty is ModuleProperty


def test_new_property_types_are_importable_from_package_root():
    from djangordf import (
        DataProperty as TopData,
        LangStringProperty as TopLang,
        ObjectProperty as TopObj,
        URIProperty as TopURI,
        LangString as TopLangString,
    )
    from djangordf.properties import (
        DataProperty, LangStringProperty, ObjectProperty, URIProperty,
    )
    from djangordf.namespaces import LangString
    assert TopData is DataProperty
    assert TopLang is LangStringProperty
    assert TopObj is ObjectProperty
    assert TopURI is URIProperty
    assert TopLangString is LangString
