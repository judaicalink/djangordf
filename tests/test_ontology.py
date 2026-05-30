"""Tests for djangordf.ontology — OWL ontology generation."""
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD


def test_empty_models_returns_graph_with_only_prefix_bindings():
    from djangordf.ontology import generate_ontology
    g = generate_ontology(models=[])
    assert isinstance(g, Graph)
    assert len(g) == 0
    bound = {p: str(ns) for p, ns in g.namespaces()}
    assert "skos" in bound
    assert "owl" in bound


def test_model_class_emits_owl_class_triple():
    from djangordf.models import RDFModel
    from djangordf.ontology import generate_ontology

    class OntA(RDFModel):
        pass

    g = generate_ontology(models=[OntA])
    assert (OntA._meta.class_iri, RDF.type, OWL.Class) in g


def test_class_label_uses_class_name():
    from djangordf.models import RDFModel
    from djangordf.ontology import generate_ontology

    class OntLabel(RDFModel):
        pass

    g = generate_ontology(models=[OntLabel])
    assert (OntLabel._meta.class_iri, RDFS.label, Literal("OntLabel")) in g


def test_class_comment_uses_first_line_of_docstring():
    from djangordf.models import RDFModel
    from djangordf.ontology import generate_ontology

    class OntComment(RDFModel):
        """A documented concept.

        Longer body follows.
        """

    g = generate_ontology(models=[OntComment])
    assert (
        OntComment._meta.class_iri,
        RDFS.comment,
        Literal("A documented concept."),
    ) in g


def test_no_comment_when_class_has_no_docstring():
    from djangordf.models import RDFModel
    from djangordf.ontology import generate_ontology

    class OntNoComment(RDFModel):
        pass

    g = generate_ontology(models=[OntNoComment])
    assert (OntNoComment._meta.class_iri, RDFS.comment, None) not in g
    comments = list(g.objects(OntNoComment._meta.class_iri, RDFS.comment))
    assert comments == []


def test_subclass_relationship_emits_rdfs_subclassof():
    from djangordf.models import RDFModel
    from djangordf.ontology import generate_ontology

    class OntBase(RDFModel):
        class Meta:
            class_iri = "http://example.org/Base"

    class OntDerived(OntBase):
        class Meta:
            class_iri = "http://example.org/Derived"

    g = generate_ontology(models=[OntBase, OntDerived])
    assert (
        OntDerived._meta.class_iri,
        RDFS.subClassOf,
        OntBase._meta.class_iri,
    ) in g
    assert (
        OntBase._meta.class_iri,
        RDFS.subClassOf,
        OntDerived._meta.class_iri,
    ) not in g


def test_custom_dataproperty_declared_as_owl_datatype_property():
    from djangordf import DataProperty, RDFModel
    from djangordf.ontology import generate_ontology

    class OntData(RDFModel):
        title = DataProperty(
            predicate=URIRef("http://example.org/title"),
            datatype=XSD.string,
        )

    g = generate_ontology(models=[OntData])
    assert (
        URIRef("http://example.org/title"),
        RDF.type,
        OWL.DatatypeProperty,
    ) in g


def test_custom_objectproperty_declared_as_owl_object_property():
    from djangordf import ObjectProperty, RDFModel
    from djangordf.ontology import generate_ontology

    class OntObjTarget(RDFModel):
        class Meta:
            class_iri = "http://example.org/Target"

    class OntObj(RDFModel):
        link = ObjectProperty(
            OntObjTarget,
            predicate=URIRef("http://example.org/link"),
        )

    g = generate_ontology(models=[OntObj, OntObjTarget])
    assert (
        URIRef("http://example.org/link"),
        RDF.type,
        OWL.ObjectProperty,
    ) in g


def test_uriproperty_declared_as_owl_object_property():
    from djangordf import RDFModel, URIProperty
    from djangordf.ontology import generate_ontology

    class OntUri(RDFModel):
        homepage = URIProperty(predicate=URIRef("http://example.org/hp"))

    g = generate_ontology(models=[OntUri])
    assert (
        URIRef("http://example.org/hp"),
        RDF.type,
        OWL.ObjectProperty,
    ) in g


def test_langstring_property_uses_rdf_langstring_range():
    from djangordf import LangStringProperty, RDFModel
    from djangordf.ontology import generate_ontology

    class OntLang(RDFModel):
        label = LangStringProperty(predicate=URIRef("http://example.org/lbl"))

    g = generate_ontology(models=[OntLang])
    assert (
        URIRef("http://example.org/lbl"),
        RDFS.range,
        RDF.langString,
    ) in g


def test_dataproperty_range_defaults_to_xsd_string():
    from djangordf import DataProperty, RDFModel
    from djangordf.ontology import generate_ontology

    class OntDefaultRange(RDFModel):
        name = DataProperty(predicate=URIRef("http://example.org/name"))

    g = generate_ontology(models=[OntDefaultRange])
    assert (
        URIRef("http://example.org/name"),
        RDFS.range,
        XSD.string,
    ) in g


def test_objectproperty_range_is_target_class_iri():
    from djangordf import ObjectProperty, RDFModel
    from djangordf.ontology import generate_ontology

    class OntTargetCls(RDFModel):
        class Meta:
            class_iri = "http://example.org/Target2"

    class OntRefCls(RDFModel):
        link = ObjectProperty(
            OntTargetCls,
            predicate=URIRef("http://example.org/link2"),
        )

    g = generate_ontology(models=[OntRefCls, OntTargetCls])
    assert (
        URIRef("http://example.org/link2"),
        RDFS.range,
        OntTargetCls._meta.class_iri,
    ) in g


def test_external_predicate_not_redeclared():
    """A property using a SKOS predicate must NOT emit `owl:DatatypeProperty`
    nor `owl:ObjectProperty` for that predicate — the SKOS ontology
    already declares it."""
    from djangordf import LangStringProperty, RDFModel
    from djangordf.ontology import generate_ontology

    class OntSkos(RDFModel):
        pref_label = LangStringProperty(many=True)

    g = generate_ontology(models=[OntSkos])
    assert (SKOS.prefLabel, RDF.type, OWL.DatatypeProperty) not in g
    assert (SKOS.prefLabel, RDF.type, OWL.ObjectProperty) not in g


def test_external_predicate_still_gets_domain_and_range():
    from djangordf import LangStringProperty, RDFModel
    from djangordf.ontology import generate_ontology

    class OntSkosDR(RDFModel):
        pref_label = LangStringProperty(many=True)

    g = generate_ontology(models=[OntSkosDR])
    assert (
        SKOS.prefLabel,
        RDFS.domain,
        OntSkosDR._meta.class_iri,
    ) in g
    assert (SKOS.prefLabel, RDFS.range, RDF.langString) in g


def test_required_property_emits_min_cardinality_restriction():
    from djangordf import DataProperty, RDFModel
    from djangordf.ontology import generate_ontology

    p = URIRef("http://example.org/required")

    class OntReq(RDFModel):
        title = DataProperty(predicate=p, required=True)

    g = generate_ontology(models=[OntReq])
    bnodes = list(g.objects(OntReq._meta.class_iri, RDFS.subClassOf))
    bnodes = [b for b in bnodes if isinstance(b, BNode)]
    found = False
    for b in bnodes:
        if (b, OWL.onProperty, p) in g and (
            b,
            OWL.minCardinality,
            Literal(1, datatype=XSD.nonNegativeInteger),
        ) in g:
            found = True
            break
    assert found, "expected an owl:Restriction with min cardinality 1"


def test_many_false_property_emits_max_cardinality_restriction():
    from djangordf import DataProperty, RDFModel
    from djangordf.ontology import generate_ontology

    p = URIRef("http://example.org/single")

    class OntSingle(RDFModel):
        title = DataProperty(predicate=p)

    g = generate_ontology(models=[OntSingle])
    bnodes = [
        b for b in g.objects(OntSingle._meta.class_iri, RDFS.subClassOf)
        if isinstance(b, BNode)
    ]
    found = False
    for b in bnodes:
        if (b, OWL.onProperty, p) in g and (
            b,
            OWL.maxCardinality,
            Literal(1, datatype=XSD.nonNegativeInteger),
        ) in g:
            found = True
            break
    assert found, "expected an owl:Restriction with max cardinality 1"


def test_many_true_not_required_emits_no_restriction():
    from djangordf import DataProperty, RDFModel
    from djangordf.ontology import generate_ontology

    p = URIRef("http://example.org/many-not-required")

    class OntMany(RDFModel):
        tags = DataProperty(predicate=p, many=True)

    g = generate_ontology(models=[OntMany])
    bnodes = [
        b for b in g.objects(OntMany._meta.class_iri, RDFS.subClassOf)
        if isinstance(b, BNode)
    ]
    assert bnodes == []


def test_graph_has_prefix_bindings_from_registry():
    from djangordf.ontology import generate_ontology

    g = generate_ontology(models=[])
    prefixes = {p for p, _ in g.namespaces()}
    for required in ("rdf", "rdfs", "owl", "xsd", "skos", "dct", "foaf"):
        assert required in prefixes


def test_generate_ontology_is_importable_from_package_root():
    from djangordf import generate_ontology as top_level
    from djangordf.ontology import generate_ontology as module_level
    assert top_level is module_level
