"""In-memory triple-store backend using rdflib's ConjunctiveGraph."""
from typing import Iterable, Optional, Union

from rdflib import ConjunctiveGraph, URIRef
from rdflib.graph import Graph
from rdflib.query import Result

from .base import Triple, TriplePattern, TripleStoreBackend


class InMemoryBackend(TripleStoreBackend):
    """Triple-store backend that keeps all data in process memory.

    Powers unit tests and the local quickstart. SPARQL queries and
    updates are dispatched directly to rdflib's own engine.
    """

    def __init__(self) -> None:
        self._store = ConjunctiveGraph()

    def query(self, sparql: str) -> Union[Result, Graph]:
        result = self._store.query(sparql)
        if result.type in ("CONSTRUCT", "DESCRIBE") and result.graph is not None:
            return result.graph
        return result

    def update(self, sparql: str) -> None:
        self._store.update(sparql)

    def add(
        self,
        triples: Iterable[Triple],
        graph: Optional[URIRef] = None,
    ) -> None:
        target = self._target(graph)
        for triple in triples:
            target.add(triple)

    def remove(
        self,
        pattern: TriplePattern,
        graph: Optional[URIRef] = None,
    ) -> None:
        self._target(graph).remove(pattern)

    def clear(self, graph: Optional[URIRef] = None) -> None:
        self._target(graph).remove((None, None, None))

    def _target(self, graph: Optional[URIRef]) -> Graph:
        if graph is None:
            return self._store.default_context
        return self._store.get_context(graph)
