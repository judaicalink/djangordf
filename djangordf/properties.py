"""Declarative property descriptors for RDFModel.

Only the bare minimum that the metaclass needs to recognise a property
declaration lives here. The full type system (DataProperty,
LangStringProperty, ObjectProperty, URIProperty) is implemented in
issue #7.
"""
from typing import Optional

from rdflib import URIRef


class Property:
    """Base class for declarative property descriptors."""

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

    def contribute_to_class(self, attr_name: str) -> None:
        self.attr_name = attr_name

    def default(self):
        if self.many:
            return []
        return self._default
