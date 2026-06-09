"""Declarative property descriptors for RDFModel.

Property type system (issue #7). The metaclass collects ``Property``
instances at class creation, hands each one the owner class via
``contribute_to_class``, and later delegates RDF serialisation /
deserialisation to ``to_rdf`` / ``from_rdf`` per property.
"""
from typing import Optional

from rdflib import Literal, URIRef

from .namespaces import LangString


class Property:
    """Base class for declarative property descriptors.

    Subclasses override ``to_rdf`` and ``from_rdf`` to map Python values
    to RDF terms and back. The base implementation is a no-op so simple
    direct uses of ``Property`` keep working — useful for tests that
    only need a predicate stub.
    """

    def __init__(
        self,
        predicate: Optional[URIRef] = None,
        *,
        many: bool = False,
        required: bool = False,
        default=None,
    ) -> None:
        self.predicate = URIRef(predicate) if predicate is not None else None
        self.many = many
        self.required = required
        self._default = default
        self.attr_name: Optional[str] = None
        self.owner_class = None

    def contribute_to_class(self, attr_name: str, owner_class=None) -> None:
        self.attr_name = attr_name
        if owner_class is not None:
            self.owner_class = owner_class

    def default(self):
        if self.many:
            return []
        return self._default

    # -- RDF serialisation extension points ---------------------------------

    def to_rdf(self, subject, value):
        """Return the triples this property contributes for ``value``.

        Default implementation: emit no triples. Concrete subclasses
        override.
        """
        return []

    def from_rdf(self, graph, subject):
        """Read this property's value back out of a graph.

        Default implementation returns ``None`` (scalar) or ``[]``
        (many).
        """
        return [] if self.many else None


class DataProperty(Property):
    """Typed-literal data property (xsd:string, xsd:integer, ...)."""

    def __init__(
        self,
        predicate: Optional[URIRef] = None,
        *,
        datatype: Optional[URIRef] = None,
        many: bool = False,
        required: bool = False,
        default=None,
    ) -> None:
        super().__init__(
            predicate,
            many=many,
            required=required,
            default=default,
        )
        self.datatype = (
            URIRef(datatype) if datatype is not None else None
        )

    def to_rdf(self, subject, value):
        if value is None:
            return []
        if self.many:
            return [
                (subject, self.predicate, Literal(v, datatype=self.datatype))
                for v in value
            ]
        return [
            (subject, self.predicate, Literal(value, datatype=self.datatype))
        ]

    def from_rdf(self, graph, subject):
        objects = list(graph.objects(subject, self.predicate))
        if self.many:
            return [self._coerce(o) for o in objects]
        if not objects:
            return None
        return self._coerce(objects[0])

    @staticmethod
    def _coerce(literal):
        try:
            return literal.toPython()
        except Exception:
            return str(literal)


class LangStringProperty(Property):
    """Language-tagged string property mapping to ``rdf:langString``."""

    def to_rdf(self, subject, value):
        if value is None:
            return []
        if self.many:
            return [
                (subject, self.predicate, Literal(ls.value, lang=ls.lang))
                for ls in value
            ]
        return [
            (subject, self.predicate, Literal(value.value, lang=value.lang))
        ]

    def from_rdf(self, graph, subject):
        objects = list(graph.objects(subject, self.predicate))
        results = [
            LangString(str(o), o.language)
            for o in objects
            if getattr(o, "language", None) is not None
        ]
        if self.many:
            return results
        return results[0] if results else None


class URIProperty(Property):
    """Raw-IRI property (no Python wrapper, just ``URIRef``)."""

    def to_rdf(self, subject, value):
        if value is None:
            return []
        if self.many:
            return [
                (subject, self.predicate, URIRef(v))
                for v in value
            ]
        return [(subject, self.predicate, URIRef(value))]

    def from_rdf(self, graph, subject):
        objects = list(graph.objects(subject, self.predicate))
        if self.many:
            return [URIRef(o) for o in objects]
        return URIRef(objects[0]) if objects else None


class ObjectProperty(Property):
    """Link between two RDFModel instances.

    ``target`` may be the target class, the string ``"self"``, or the
    name of a registered model class — the last two resolve lazily
    through ``djangordf.models.get_registered_model`` the first time
    ``target_class`` is accessed.

    ``inverse`` names a property declared on the target class. When
    present, saving an instance also writes the mirror triple
    ``(target.iri, inverse_predicate, self.iri)`` and deletes any
    stale mirror triples pointing at this instance via the inverse
    predicate. The resolution is lazy — accessing ``inverse_property``
    or ``inverse_predicate`` for the first time looks up the
    referenced attribute on the target class.

    ``reverse=True`` declares a read-only virtual property whose
    triples live on the target class's forward predicate. Saving an
    instance emits **no** triples for this property; reading hydrates
    target-class ghost instances by looking up subjects that point at
    this instance via ``predicate``. Filter paths through a reverse
    segment swap subject and object so the generated SPARQL traverses
    the inverse direction. ``reverse=True`` is mutually exclusive
    with ``inverse=<name>`` (the latter implies mirror writes, which
    contradicts read-only semantics).
    """

    def __init__(
        self,
        target,
        predicate: Optional[URIRef] = None,
        *,
        many: bool = False,
        required: bool = False,
        default=None,
        inverse: Optional[str] = None,
        reverse: bool = False,
    ) -> None:
        super().__init__(
            predicate,
            many=many,
            required=required,
            default=default,
        )
        if reverse and inverse is not None:
            raise ValueError(
                "ObjectProperty cannot combine reverse=True with "
                "inverse=...; reverse is read-only"
            )
        self._target = target
        self.inverse = inverse
        self.reverse = reverse

    @property
    def target_class(self):
        if isinstance(self._target, type):
            return self._target
        if self._target == "self":
            return self.owner_class
        from .models import get_registered_model
        return get_registered_model(self._target)

    @property
    def inverse_property(self):
        """Resolve ``inverse`` to the matching ``Property`` on the
        target class. Returns ``None`` if no inverse was declared;
        raises ``ValueError`` if the name does not resolve."""
        if self.inverse is None:
            return None
        target_cls = self.target_class
        try:
            return target_cls._properties[self.inverse]
        except KeyError as exc:
            raise ValueError(
                f"inverse {self.inverse!r} is not declared on "
                f"{target_cls.__name__}"
            ) from exc

    @property
    def inverse_predicate(self):
        """``URIRef`` predicate of the resolved inverse property,
        or ``None`` if no inverse was declared."""
        prop = self.inverse_property
        return prop.predicate if prop is not None else None

    def to_rdf(self, subject, value):
        if self.reverse:
            return []
        if value is None:
            return []
        if self.many:
            return [
                (subject, self.predicate, self._iri_of(v))
                for v in value
            ]
        return [(subject, self.predicate, self._iri_of(value))]

    def from_rdf(self, graph, subject):
        if self.reverse:
            objects = list(graph.subjects(self.predicate, subject))
        else:
            objects = list(graph.objects(subject, self.predicate))
        target_cls = self.target_class
        if self.many:
            return [target_cls(iri=URIRef(o)) for o in objects]
        if not objects:
            return None
        return target_cls(iri=URIRef(objects[0]))

    @staticmethod
    def _iri_of(value):
        if isinstance(value, URIRef):
            return value
        return URIRef(value.iri)
