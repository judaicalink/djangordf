"""Tests for djangordf.properties (minimal base in this milestone)."""
from rdflib import URIRef


def test_property_stores_predicate():
    from djangordf.properties import Property
    p = Property(predicate=URIRef("http://example.org/p"))
    assert p.predicate == URIRef("http://example.org/p")


def test_property_predicate_defaults_to_none():
    from djangordf.properties import Property
    p = Property()
    assert p.predicate is None


def test_contribute_to_class_records_attribute_name():
    from djangordf.properties import Property
    p = Property()
    p.contribute_to_class("pref_label")
    assert p.attr_name == "pref_label"


def test_property_to_rdf_emits_no_triples_for_none_value():
    from rdflib import URIRef
    from djangordf.properties import Property
    p = Property(predicate=URIRef("http://example.org/p"))
    triples = p.to_rdf(URIRef("http://example.org/s"), None)
    assert triples == []


def test_property_from_rdf_returns_none_when_no_match():
    from rdflib import Graph, URIRef
    from djangordf.properties import Property
    p = Property(predicate=URIRef("http://example.org/p"))
    assert p.from_rdf(Graph(), URIRef("http://example.org/s")) is None


def test_property_contribute_to_class_accepts_owner_class():
    from djangordf.properties import Property
    p = Property()
    p.contribute_to_class("title", owner_class=object)
    assert p.attr_name == "title"
    assert p.owner_class is object


# -- DataProperty -----------------------------------------------------------


def test_data_property_scalar_to_rdf_emits_typed_literal():
    from rdflib import Literal, URIRef
    from rdflib.namespace import XSD
    from djangordf.properties import DataProperty

    prop = DataProperty(
        predicate=URIRef("http://example.org/count"),
        datatype=XSD.integer,
    )
    triples = prop.to_rdf(URIRef("http://example.org/s"), 42)
    assert triples == [
        (
            URIRef("http://example.org/s"),
            URIRef("http://example.org/count"),
            Literal(42, datatype=XSD.integer),
        )
    ]


def test_data_property_scalar_to_rdf_skips_none():
    from rdflib import URIRef
    from rdflib.namespace import XSD
    from djangordf.properties import DataProperty

    prop = DataProperty(
        predicate=URIRef("http://example.org/count"),
        datatype=XSD.integer,
    )
    assert prop.to_rdf(URIRef("http://example.org/s"), None) == []


def test_data_property_many_to_rdf_emits_one_triple_per_value():
    from rdflib import URIRef
    from rdflib.namespace import XSD
    from djangordf.properties import DataProperty

    prop = DataProperty(
        predicate=URIRef("http://example.org/n"),
        datatype=XSD.integer,
        many=True,
    )
    triples = prop.to_rdf(URIRef("http://example.org/s"), [1, 2, 3])
    assert len(triples) == 3
    objects = sorted(int(t[2]) for t in triples)
    assert objects == [1, 2, 3]


def test_data_property_scalar_from_rdf_returns_python_value():
    from rdflib import Graph, Literal, URIRef
    from rdflib.namespace import XSD
    from djangordf.properties import DataProperty

    g = Graph()
    s = URIRef("http://example.org/s")
    p = URIRef("http://example.org/count")
    g.add((s, p, Literal(42, datatype=XSD.integer)))

    prop = DataProperty(predicate=p, datatype=XSD.integer)
    assert prop.from_rdf(g, s) == 42


def test_data_property_many_from_rdf_returns_list_of_values():
    from rdflib import Graph, Literal, URIRef
    from rdflib.namespace import XSD
    from djangordf.properties import DataProperty

    g = Graph()
    s = URIRef("http://example.org/s")
    p = URIRef("http://example.org/n")
    for v in (1, 2, 3):
        g.add((s, p, Literal(v, datatype=XSD.integer)))

    prop = DataProperty(predicate=p, datatype=XSD.integer, many=True)
    assert sorted(prop.from_rdf(g, s)) == [1, 2, 3]


def test_data_property_scalar_from_rdf_returns_none_when_missing():
    from rdflib import Graph, URIRef
    from rdflib.namespace import XSD
    from djangordf.properties import DataProperty

    prop = DataProperty(
        predicate=URIRef("http://example.org/p"),
        datatype=XSD.integer,
    )
    assert prop.from_rdf(Graph(), URIRef("http://example.org/s")) is None


# -- LangStringProperty -----------------------------------------------------


def test_lang_string_property_scalar_to_rdf():
    from rdflib import Literal, URIRef
    from djangordf.namespaces import LangString
    from djangordf.properties import LangStringProperty

    prop = LangStringProperty(
        predicate=URIRef("http://example.org/label")
    )
    triples = prop.to_rdf(
        URIRef("http://example.org/s"),
        LangString("Buch", "de"),
    )
    assert triples == [
        (
            URIRef("http://example.org/s"),
            URIRef("http://example.org/label"),
            Literal("Buch", lang="de"),
        )
    ]


def test_lang_string_property_many_to_rdf():
    from rdflib import URIRef
    from djangordf.namespaces import LangString
    from djangordf.properties import LangStringProperty

    prop = LangStringProperty(
        predicate=URIRef("http://example.org/label"),
        many=True,
    )
    triples = prop.to_rdf(
        URIRef("http://example.org/s"),
        [LangString("Buch", "de"), LangString("Book", "en")],
    )
    assert len(triples) == 2
    langs = sorted(t[2].language for t in triples)
    assert langs == ["de", "en"]


def test_lang_string_property_from_rdf_round_trip():
    from rdflib import Graph, Literal, URIRef
    from djangordf.namespaces import LangString
    from djangordf.properties import LangStringProperty

    g = Graph()
    s = URIRef("http://example.org/s")
    p = URIRef("http://example.org/label")
    g.add((s, p, Literal("Buch", lang="de")))
    g.add((s, p, Literal("Book", lang="en")))

    prop = LangStringProperty(predicate=p, many=True)
    result = prop.from_rdf(g, s)
    assert set(result) == {
        LangString("Buch", "de"),
        LangString("Book", "en"),
    }


def test_lang_string_property_scalar_from_rdf_missing_returns_none():
    from rdflib import Graph, URIRef
    from djangordf.properties import LangStringProperty

    prop = LangStringProperty(
        predicate=URIRef("http://example.org/label")
    )
    assert prop.from_rdf(Graph(), URIRef("http://example.org/s")) is None


# -- URIProperty ------------------------------------------------------------


def test_uri_property_scalar_to_rdf_accepts_string_or_uriref():
    from rdflib import URIRef
    from djangordf.properties import URIProperty

    prop = URIProperty(
        predicate=URIRef("http://example.org/exactMatch")
    )

    from_str = prop.to_rdf(
        URIRef("http://example.org/s"),
        "http://example.org/o",
    )
    from_uri = prop.to_rdf(
        URIRef("http://example.org/s"),
        URIRef("http://example.org/o"),
    )
    assert from_str == from_uri
    assert from_str[0][2] == URIRef("http://example.org/o")


def test_uri_property_many_to_rdf():
    from rdflib import URIRef
    from djangordf.properties import URIProperty

    prop = URIProperty(
        predicate=URIRef("http://example.org/seeAlso"),
        many=True,
    )
    triples = prop.to_rdf(
        URIRef("http://example.org/s"),
        [
            "http://example.org/a",
            URIRef("http://example.org/b"),
        ],
    )
    assert len(triples) == 2
    targets = {t[2] for t in triples}
    assert URIRef("http://example.org/a") in targets
    assert URIRef("http://example.org/b") in targets


def test_uri_property_from_rdf_returns_uriref():
    from rdflib import Graph, URIRef
    from djangordf.properties import URIProperty

    g = Graph()
    s = URIRef("http://example.org/s")
    p = URIRef("http://example.org/exactMatch")
    g.add((s, p, URIRef("http://example.org/o")))

    prop = URIProperty(predicate=p)
    result = prop.from_rdf(g, s)
    assert isinstance(result, URIRef)
    assert str(result) == "http://example.org/o"


# -- ObjectProperty ---------------------------------------------------------


def test_object_property_to_rdf_takes_rdf_model_instance():
    from rdflib import URIRef
    from djangordf.models import RDFModel
    from djangordf.properties import ObjectProperty

    class TargetA(RDFModel):
        pass

    target = TargetA(iri="http://example.org/target/1")
    prop = ObjectProperty(
        TargetA,
        predicate=URIRef("http://example.org/related"),
    )
    triples = prop.to_rdf(
        URIRef("http://example.org/s"), target,
    )
    assert triples == [
        (
            URIRef("http://example.org/s"),
            URIRef("http://example.org/related"),
            URIRef("http://example.org/target/1"),
        )
    ]


def test_object_property_to_rdf_accepts_uriref_too():
    from rdflib import URIRef
    from djangordf.models import RDFModel
    from djangordf.properties import ObjectProperty

    class TargetB(RDFModel):
        pass

    prop = ObjectProperty(
        TargetB,
        predicate=URIRef("http://example.org/related"),
    )
    triples = prop.to_rdf(
        URIRef("http://example.org/s"),
        URIRef("http://example.org/target/2"),
    )
    assert triples[0][2] == URIRef("http://example.org/target/2")


def test_object_property_many_to_rdf():
    from rdflib import URIRef
    from djangordf.models import RDFModel
    from djangordf.properties import ObjectProperty

    class TargetC(RDFModel):
        pass

    a = TargetC(iri="http://example.org/c/a")
    b = TargetC(iri="http://example.org/c/b")
    prop = ObjectProperty(
        TargetC,
        predicate=URIRef("http://example.org/related"),
        many=True,
    )
    triples = prop.to_rdf(URIRef("http://example.org/s"), [a, b])
    targets = {t[2] for t in triples}
    assert targets == {
        URIRef("http://example.org/c/a"),
        URIRef("http://example.org/c/b"),
    }


def test_object_property_from_rdf_returns_target_instance():
    """``from_rdf`` materialises target-class instances carrying only
    ``.iri``. Loading the rest of the target's state remains the
    caller's job (``target_cls.objects.get(.iri)``)."""
    from rdflib import Graph, URIRef
    from djangordf.models import RDFModel
    from djangordf.properties import ObjectProperty

    class TargetD(RDFModel):
        pass

    g = Graph()
    s = URIRef("http://example.org/s")
    p = URIRef("http://example.org/related")
    g.add((s, p, URIRef("http://example.org/d/1")))

    prop = ObjectProperty(TargetD, predicate=p)
    result = prop.from_rdf(g, s)
    assert isinstance(result, TargetD)
    assert result.iri == URIRef("http://example.org/d/1")


def test_object_property_self_target_resolves_to_owner_class():
    from djangordf.models import RDFModel
    from djangordf.properties import ObjectProperty

    class TermSelf(RDFModel):
        broader = ObjectProperty("self")

    prop = TermSelf._properties["broader"]
    assert prop.target_class is TermSelf


def test_object_property_string_target_resolves_through_registry():
    from djangordf.models import RDFModel
    from djangordf.properties import ObjectProperty

    class TargetByName(RDFModel):
        pass

    class Referrer(RDFModel):
        link = ObjectProperty("TargetByName")

    prop = Referrer._properties["link"]
    assert prop.target_class is TargetByName
