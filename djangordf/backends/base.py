"""Abstract base class every triple-store backend must implement."""
from abc import ABC, abstractmethod
from typing import Iterable, Optional, Tuple, Union

from rdflib import URIRef
from rdflib.graph import Graph
from rdflib.query import Result


Triple = Tuple[object, object, object]
TriplePattern = Tuple[Optional[object], Optional[object], Optional[object]]


class TripleStoreBackend(ABC):
    """The contract a triple-store backend must fulfil.

    Intentionally narrow: SPARQL 1.1 query and update plus convenience
    helpers for bulk add, pattern-based remove, and clearing a graph.
    Anything beyond (transactions, reasoning, named-graph listing) is
    opt-in via subclass extension.
    """

    @abstractmethod
    def query(self, sparql: str) -> Union[Result, Graph]:
        """Run a SPARQL SELECT, ASK, CONSTRUCT or DESCRIBE.

        Returns an rdflib ``Graph`` for CONSTRUCT/DESCRIBE and an
        rdflib ``Result`` for SELECT/ASK.
        """

    @abstractmethod
    def update(self, sparql: str) -> None:
        """Run a SPARQL UPDATE (INSERT, DELETE, CLEAR, LOAD)."""

    @abstractmethod
    def add(
        self,
        triples: Iterable[Triple],
        graph: Optional[URIRef] = None,
    ) -> None:
        """Bulk-add triples to a named graph, or the default graph if
        ``graph`` is ``None``."""

    @abstractmethod
    def remove(
        self,
        pattern: TriplePattern,
        graph: Optional[URIRef] = None,
    ) -> None:
        """Remove all triples matching ``(s, p, o)`` where any element
        may be ``None`` to act as a wildcard."""

    @abstractmethod
    def clear(self, graph: Optional[URIRef] = None) -> None:
        """Remove all triples from a named graph, or from the default
        graph if ``graph`` is ``None``."""
