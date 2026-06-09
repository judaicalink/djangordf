"""RDFModel base class, metaclass, Meta resolution, model registry."""
import uuid
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from rdflib import URIRef
from rdflib.namespace import RDF

from .manager import RDFManager
from .properties import Property
from .skos import (
    Concept as SKOS_CONCEPT,
    DEFAULT_PREDICATES,
    resolve_curie,
)


def _safe_setting(name: str):
    """Read a Django setting without forcing settings setup.

    ``LazySettings.__getattr__`` raises ``ImproperlyConfigured`` on
    first access if Django is not yet configured — even when a default
    is supplied via ``getattr(settings, name, default)``. We swallow
    that here so ``_build_meta`` (which runs at class-creation time
    for every ``RDFModel`` subclass and is therefore reachable on bare
    ``import djangordf``) falls through to its hard-coded defaults
    when Django settings have not been wired up yet.
    """
    try:
        return getattr(settings, name, None)
    except ImproperlyConfigured:
        return None


_MODEL_REGISTRY: dict = {}


def get_registered_model(name: str):
    """Look up a model class by its name. Used for string targets in
    ``ObjectProperty("self", ...)`` and forward references."""
    return _MODEL_REGISTRY[name]


@dataclass
class _MetaInfo:
    class_iri: URIRef
    namespace: URIRef
    graph_iri: URIRef


def _build_meta(name: str, meta_cls) -> _MetaInfo:
    raw_class_iri = getattr(meta_cls, "class_iri", None) if meta_cls else None
    if raw_class_iri is None:
        class_iri = SKOS_CONCEPT
    else:
        class_iri = resolve_curie(raw_class_iri)

    raw_namespace = getattr(meta_cls, "namespace", None) if meta_cls else None
    if raw_namespace is None:
        raw_namespace = _safe_setting("DJANGORDF_DEFAULT_NAMESPACE")
    if raw_namespace is None:
        raw_namespace = f"urn:djangordf:{name.lower()}:"
    namespace = URIRef(raw_namespace)

    raw_graph = getattr(meta_cls, "graph_iri", None) if meta_cls else None
    if raw_graph is None:
        raw_graph = _safe_setting("DJANGORDF_DEFAULT_GRAPH")
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
                properties[attr] = value

        cls = super().__new__(mcs, name, bases, namespace)
        cls._properties = properties

        # Now that ``cls`` exists, hand each property the owner class so
        # ObjectProperty("self") can resolve, and assign the SKOS
        # convention predicate when none was supplied explicitly.
        for attr, prop in properties.items():
            prop.contribute_to_class(attr, owner_class=cls)
            if prop.predicate is None and attr in DEFAULT_PREDICATES:
                prop.predicate = DEFAULT_PREDICATES[attr]

        if name != "RDFModel":
            meta_cls = namespace.get("Meta")
            cls._meta = _build_meta(name, meta_cls)
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

    def _to_triples(self):
        """Emit all triples this instance currently represents.

        Delegates to each property's ``to_rdf`` so concrete property
        types (DataProperty / LangStringProperty / ObjectProperty /
        URIProperty) own their own serialisation rules.
        """
        triples = [(self.iri, RDF.type, self._meta.class_iri)]
        for attr, prop in self._properties.items():
            if prop.predicate is None:
                continue
            value = getattr(self, attr, None)
            triples.extend(prop.to_rdf(self.iri, value))
        return triples

    def save(self):
        if self.iri is None:
            self.iri = URIRef(
                f"{self._meta.namespace}{uuid.uuid4().hex}"
            )
        self.objects.save(self)

    def delete(self):
        self.objects.delete(self)
