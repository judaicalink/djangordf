"""Generate an OWL ontology from declared ``RDFModel`` classes.

Walks the model registry, asks each class for its declared
properties, and emits the OWL triples that describe the schema:
``owl:Class`` declarations, ``rdfs:subClassOf`` relationships,
``rdfs:label``/``rdfs:comment`` annotations, per-property
``owl:DatatypeProperty``/``owl:ObjectProperty`` declarations (for
custom predicates only — external SKOS/FOAF/etc. predicates are not
re-declared), ``rdfs:domain``/``rdfs:range``, and blank-node
``owl:Restriction`` resources for cardinality.
"""
from typing import Iterable, List, Optional

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD

from .namespaces import registry
from .properties import (
    DataProperty,
    LangStringProperty,
    ObjectProperty,
    URIProperty,
)


_EXTERNAL_PREFIXES = frozenset(
    ["rdf", "rdfs", "owl", "xsd", "skos", "dct", "foaf"]
)


def _external_namespace_uris() -> List[str]:
    bindings = registry.bindings()
    return [str(bindings[p]) for p in _EXTERNAL_PREFIXES if p in bindings]


def _is_external_predicate(predicate: URIRef) -> bool:
    pred_str = str(predicate)
    return any(pred_str.startswith(ns) for ns in _external_namespace_uris())


def _registered_models() -> List[type]:
    from .models import _MODEL_REGISTRY
    return list(_MODEL_REGISTRY.values())


def _docstring_first_line(model) -> Optional[str]:
    if not model.__doc__:
        return None
    first = model.__doc__.strip().splitlines()[0].strip()
    return first or None


def _emit_class(graph: Graph, model) -> None:
    class_iri = model._meta.class_iri
    graph.add((class_iri, RDF.type, OWL.Class))
    graph.add((class_iri, RDFS.label, Literal(model.__name__)))
    comment = _docstring_first_line(model)
    if comment is not None:
        graph.add((class_iri, RDFS.comment, Literal(comment)))


def _emit_subclass_of(graph: Graph, model) -> None:
    from .models import RDFModel
    class_iri = model._meta.class_iri
    for base in model.__mro__[1:]:
        if base is RDFModel or base is object:
            continue
        if not isinstance(base, type) or not issubclass(base, RDFModel):
            continue
        base_meta = getattr(base, "_meta", None)
        if base_meta is None:
            continue
        graph.add((class_iri, RDFS.subClassOf, base_meta.class_iri))


def _emit_property_declaration(graph: Graph, prop) -> None:
    if _is_external_predicate(prop.predicate):
        return
    if isinstance(prop, (DataProperty, LangStringProperty)):
        graph.add((prop.predicate, RDF.type, OWL.DatatypeProperty))
    elif isinstance(prop, (ObjectProperty, URIProperty)):
        graph.add((prop.predicate, RDF.type, OWL.ObjectProperty))
    graph.add((prop.predicate, RDFS.label, Literal(prop.attr_name)))


def _range_term_for(prop):
    if isinstance(prop, LangStringProperty):
        return RDF.langString
    if isinstance(prop, DataProperty):
        return prop.datatype if prop.datatype is not None else XSD.string
    if isinstance(prop, ObjectProperty):
        target = prop.target_class
        target_meta = getattr(target, "_meta", None)
        if target_meta is not None:
            return target_meta.class_iri
        return None
    if isinstance(prop, URIProperty):
        return RDFS.Resource
    return None


def _emit_property_domain_range(graph: Graph, model, prop) -> None:
    class_iri = model._meta.class_iri
    graph.add((prop.predicate, RDFS.domain, class_iri))
    range_term = _range_term_for(prop)
    if range_term is not None:
        graph.add((prop.predicate, RDFS.range, range_term))


def _emit_cardinality_restriction(graph: Graph, model, prop) -> None:
    class_iri = model._meta.class_iri
    if getattr(prop, "required", False):
        bnode = BNode()
        graph.add((class_iri, RDFS.subClassOf, bnode))
        graph.add((bnode, RDF.type, OWL.Restriction))
        graph.add((bnode, OWL.onProperty, prop.predicate))
        graph.add((
            bnode,
            OWL.minCardinality,
            Literal(1, datatype=XSD.nonNegativeInteger),
        ))
    if not getattr(prop, "many", True):
        bnode = BNode()
        graph.add((class_iri, RDFS.subClassOf, bnode))
        graph.add((bnode, RDF.type, OWL.Restriction))
        graph.add((bnode, OWL.onProperty, prop.predicate))
        graph.add((
            bnode,
            OWL.maxCardinality,
            Literal(1, datatype=XSD.nonNegativeInteger),
        ))


def generate_ontology(
    models: Optional[Iterable[type]] = None,
    graph: Optional[Graph] = None,
) -> Graph:
    """Build an OWL ontology graph from the given ``RDFModel`` classes.

    Defaults to every class in the process-wide model registry. The
    resulting graph carries the prefix bindings of the namespace
    registry so Turtle serialisation comes out pretty.
    """
    if graph is None:
        graph = Graph()
    registry.bind_to_graph(graph)

    if models is None:
        models = _registered_models()
    models = list(models)

    for model in models:
        _emit_class(graph, model)
        _emit_subclass_of(graph, model)
        for prop in model._properties.values():
            if prop.predicate is None:
                continue
            _emit_property_declaration(graph, prop)
            _emit_property_domain_range(graph, model, prop)
            _emit_cardinality_restriction(graph, model, prop)

    _emit_inverse_of(graph, models)
    return graph


def _emit_inverse_of(graph: Graph, models: Iterable[type]) -> None:
    """Emit ``owl:inverseOf`` between every pair of predicates whose
    ``ObjectProperty`` declarations point at each other through
    ``inverse=``. Each pair is emitted only once."""
    emitted = set()
    for model in models:
        for prop in model._properties.values():
            if not isinstance(prop, ObjectProperty) or prop.inverse is None:
                continue
            inv_pred = prop.inverse_predicate
            if inv_pred is None or prop.predicate is None:
                continue
            key = tuple(sorted((str(prop.predicate), str(inv_pred))))
            if key in emitted:
                continue
            emitted.add(key)
            graph.add((prop.predicate, OWL.inverseOf, inv_pred))
