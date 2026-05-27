"""RDFModel base class, metaclass, Meta resolution, model registry."""
import uuid
from dataclasses import dataclass

from django.conf import settings
from rdflib import Literal, URIRef
from rdflib.namespace import RDF

from .manager import RDFManager
from .properties import Property
from .skos import Concept as SKOS_CONCEPT, resolve_curie


_MODEL_REGISTRY: dict = {}


def get_registered_model(name: str):
    """Look up a model class by its name. Used for string targets in
    ``ObjectProperty("self", ...)`` and forward references; the full
    Property system in #7 reads through this."""
    return _MODEL_REGISTRY[name]


@dataclass
class _MetaInfo:
    class_iri: URIRef
    namespace: URIRef
    graph_iri: URIRef


def _build_meta(name: str, meta_cls) -> _MetaInfo:
    """Resolve the inner ``Meta`` of an RDFModel subclass into a frozen
    ``_MetaInfo`` instance, applying defaults from Django settings and
    CURIE resolution where appropriate."""
    raw_class_iri = getattr(meta_cls, "class_iri", None) if meta_cls else None
    if raw_class_iri is None:
        class_iri = SKOS_CONCEPT
    else:
        class_iri = resolve_curie(raw_class_iri)

    raw_namespace = getattr(meta_cls, "namespace", None) if meta_cls else None
    if raw_namespace is None:
        raw_namespace = getattr(settings, "DJANGORDF_DEFAULT_NAMESPACE", None)
    if raw_namespace is None:
        raw_namespace = f"urn:djangordf:{name.lower()}:"
    namespace = URIRef(raw_namespace)

    raw_graph = getattr(meta_cls, "graph_iri", None) if meta_cls else None
    if raw_graph is None:
        raw_graph = getattr(settings, "DJANGORDF_DEFAULT_GRAPH", None)
    if raw_graph is None:
        raw_graph = "urn:djangordf:default"
    graph_iri = URIRef(raw_graph)

    return _MetaInfo(
        class_iri=class_iri,
        namespace=namespace,
        graph_iri=graph_iri,
    )


class RDFModelMeta(type):
    def __new__(mcs, name, bases, namespace):
        properties = {}
        for attr, value in list(namespace.items()):
            if isinstance(value, Property):
                value.contribute_to_class(attr)
                properties[attr] = value

        cls = super().__new__(mcs, name, bases, namespace)
        cls._properties = properties

        meta_cls = namespace.get("Meta")
        cls._meta = _build_meta(name, meta_cls)

        if name != "RDFModel":
            cls.DoesNotExist = type(
                "DoesNotExist", (Exception,), {}
            )
            cls.objects = RDFManager(cls)
            _MODEL_REGISTRY[name] = cls

        return cls


class RDFModel(metaclass=RDFModelMeta):
    """Base class for triple-store-backed domain models."""

    def __init__(self, *, iri=None, **kwargs):
        self.iri = URIRef(iri) if iri is not None else None
        for attr, prop in self._properties.items():
            setattr(self, attr, kwargs.get(attr, prop.default()))

    # -- identity by IRI ----------------------------------------------------

    def __eq__(self, other):
        if not isinstance(other, RDFModel):
            return NotImplemented
        if self.iri is None or other.iri is None:
            return self is other
        return self.iri == other.iri

    def __hash__(self):
        if self.iri is None:
            return object.__hash__(self)
        return hash(self.iri)

    # -- serialisation ------------------------------------------------------

    def _to_triples(self):
        """Triples this instance should currently hold in the store.

        The full property->RDF mapping lands in #7. This milestone
        emits ``rdf:type`` plus any value whose Property declares an
        explicit predicate.
        """
        triples = [(self.iri, RDF.type, self._meta.class_iri)]
        for attr, prop in self._properties.items():
            if prop.predicate is None:
                continue
            value = getattr(self, attr, None)
            if value is None:
                continue
            if isinstance(value, URIRef):
                obj = value
            elif isinstance(value, Literal):
                obj = value
            else:
                obj = Literal(value)
            triples.append((self.iri, prop.predicate, obj))
        return triples

    # -- persistence facade -------------------------------------------------

    def save(self):
        if self.iri is None:
            self.iri = URIRef(
                f"{self._meta.namespace}{uuid.uuid4().hex}"
            )
        self.objects.save(self)

    def delete(self):
        self.objects.delete(self)
