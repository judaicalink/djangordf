"""Declarative property descriptors for RDFModel.

Property type system (issue #7). The metaclass collects ``Property``
instances at class creation, hands each one the owner class via
``contribute_to_class``, and later delegates RDF serialisation /
deserialisation to ``to_rdf`` / ``from_rdf`` per property.
"""
from typing import Optional

from rdflib import URIRef


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
