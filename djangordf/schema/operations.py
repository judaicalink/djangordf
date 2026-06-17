"""Operation types that can appear in a ``Migration.operations`` list.

All operations carry their own ``apply(backend)`` method. Operations
are forward-only in this release; rollback support is a separate
ticket.
"""
from typing import Optional, Union

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from rdflib import Literal, URIRef


_DEFAULT_ONTOLOGY_GRAPH = URIRef("urn:djangordf:ontology")


def _ontology_graph() -> URIRef:
    """Resolve the configured ontology graph IRI; falls back gracefully
    when Django settings are not yet wired up."""
    try:
        configured = getattr(settings, "DJANGORDF_ONTOLOGY_GRAPH", None)
    except ImproperlyConfigured:
        configured = None
    if configured is None:
        return _DEFAULT_ONTOLOGY_GRAPH
    return URIRef(configured)


class Operation:
    """Marker base class for migration operations."""

    def apply(self, backend) -> None:
        raise NotImplementedError


class RunSPARQL(Operation):
    """Run an arbitrary SPARQL UPDATE statement against the backend.

    The escape hatch for transformations that do not fit any of the
    higher-level operations.
    """

    def __init__(self, sparql: str):
        self.sparql = sparql

    def apply(self, backend) -> None:
        backend.update(self.sparql)


class CreateClass(Operation):
    """Append an ``owl:Class`` declaration to the ontology graph.

    Optionally writes ``rdfs:label`` and ``rdfs:comment`` annotations
    alongside.
    """

    def __init__(
        self,
        class_iri: Union[str, URIRef],
        *,
        label: Optional[str] = None,
        comment: Optional[str] = None,
        graph: Optional[Union[str, URIRef]] = None,
    ):
        self.class_iri = URIRef(class_iri)
        self.label = label
        self.comment = comment
        self.graph = URIRef(graph) if graph is not None else None

    def apply(self, backend) -> None:
        target = self.graph or _ontology_graph()
        triples = [(
            self.class_iri,
            URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
            URIRef("http://www.w3.org/2002/07/owl#Class"),
        )]
        if self.label is not None:
            triples.append((
                self.class_iri,
                URIRef("http://www.w3.org/2000/01/rdf-schema#label"),
                Literal(self.label),
            ))
        if self.comment is not None:
            triples.append((
                self.class_iri,
                URIRef("http://www.w3.org/2000/01/rdf-schema#comment"),
                Literal(self.comment),
            ))
        backend.add(triples, graph=target)


class DeleteClass(Operation):
    """Strip every triple whose subject is the class IRI from the
    ontology graph."""

    def __init__(
        self,
        class_iri: Union[str, URIRef],
        *,
        graph: Optional[Union[str, URIRef]] = None,
    ):
        self.class_iri = URIRef(class_iri)
        self.graph = URIRef(graph) if graph is not None else None

    def apply(self, backend) -> None:
        target = self.graph or _ontology_graph()
        backend.update(
            f"WITH <{target}> "
            f"DELETE {{ <{self.class_iri}> ?p ?o }} "
            f"WHERE {{ <{self.class_iri}> ?p ?o }}"
        )


class AddPropertyDeclaration(Operation):
    """Declare a predicate in the ontology graph.

    ``kind`` is either ``"datatype"`` or ``"object"``. Domain and
    range are optional; when present they are emitted as
    ``rdfs:domain`` / ``rdfs:range`` triples on the predicate IRI.
    """

    _DATATYPE = URIRef("http://www.w3.org/2002/07/owl#DatatypeProperty")
    _OBJECT = URIRef("http://www.w3.org/2002/07/owl#ObjectProperty")

    def __init__(
        self,
        predicate: Union[str, URIRef],
        *,
        kind: str,
        domain: Optional[Union[str, URIRef]] = None,
        range: Optional[Union[str, URIRef]] = None,
        graph: Optional[Union[str, URIRef]] = None,
    ):
        if kind not in ("datatype", "object"):
            raise ValueError(
                f"AddPropertyDeclaration kind must be 'datatype' or "
                f"'object'; got {kind!r}"
            )
        self.predicate = URIRef(predicate)
        self.kind = kind
        self.domain = URIRef(domain) if domain is not None else None
        # ``range`` shadows the builtin only inside this function; that
        # mirrors rdflib's own naming convention.
        self.range = URIRef(range) if range is not None else None
        self.graph = URIRef(graph) if graph is not None else None

    def apply(self, backend) -> None:
        target = self.graph or _ontology_graph()
        rdf_type = URIRef(
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        )
        type_iri = self._DATATYPE if self.kind == "datatype" else self._OBJECT
        triples = [(self.predicate, rdf_type, type_iri)]
        if self.domain is not None:
            triples.append((
                self.predicate,
                URIRef("http://www.w3.org/2000/01/rdf-schema#domain"),
                self.domain,
            ))
        if self.range is not None:
            triples.append((
                self.predicate,
                URIRef("http://www.w3.org/2000/01/rdf-schema#range"),
                self.range,
            ))
        backend.add(triples, graph=target)


class RenamePredicate(Operation):
    """Rewrite every ``(?s, old, ?o)`` triple to ``(?s, new, ?o)``.

    Runs across the data graph by default; an explicit ``graph=``
    targets a specific named graph. Useful when the user-facing name
    of a property changes but the data should remain.
    """

    def __init__(
        self,
        old: Union[str, URIRef],
        new: Union[str, URIRef],
        *,
        graph: Optional[Union[str, URIRef]] = None,
    ):
        self.old = URIRef(old)
        self.new = URIRef(new)
        self.graph = URIRef(graph) if graph is not None else None

    def apply(self, backend) -> None:
        if self.graph is not None:
            backend.update(
                f"WITH <{self.graph}> "
                f"INSERT {{ ?s <{self.new}> ?o }} "
                f"WHERE {{ ?s <{self.old}> ?o }} ;"
                f"WITH <{self.graph}> "
                f"DELETE {{ ?s <{self.old}> ?o }} "
                f"WHERE {{ ?s <{self.old}> ?o }}"
            )
        else:
            backend.update(
                f"INSERT {{ ?s <{self.new}> ?o }} "
                f"WHERE {{ ?s <{self.old}> ?o }} ;"
                f"DELETE {{ ?s <{self.old}> ?o }} "
                f"WHERE {{ ?s <{self.old}> ?o }}"
            )
