"""Reasoner ABC plus the public ``materialize`` entry point."""
from typing import List, Optional, Sequence, Union

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string
from rdflib import URIRef

from ..conf import get_backend


_DEFAULT_INTERNAL_GRAPH = URIRef("urn:djangordf:default")


def _resolve_graph(value, fallback) -> URIRef:
    if value is None:
        return fallback
    return URIRef(value)


def _backend_triple_count(backend, graph_iri: URIRef) -> int:
    sparql = (
        "SELECT (COUNT(*) AS ?n) WHERE { "
        f"GRAPH <{graph_iri}> {{ ?s ?p ?o }} }}"
    )
    result = backend.query(sparql)
    for row in result:
        return int(row[0])
    return 0


class Reasoner:
    """Base class for reasoners.

    Subclasses override :meth:`rules` (returning a sequence of
    SPARQL ``INSERT-WHERE`` strings) to declare their inference
    rules. The base :meth:`materialize` runs them in a fixpoint
    loop. Override :meth:`materialize` directly for non-SPARQL
    reasoners (see :class:`OWLRLReasoner`).
    """

    def rules(self, source_graph: URIRef, target_graph: URIRef) -> Sequence[str]:
        """Return the SPARQL ``INSERT-WHERE`` strings for one pass."""
        raise NotImplementedError

    def materialize(
        self,
        backend=None,
        *,
        source_graph=None,
        target_graph=None,
        max_iterations: int = 50,
    ) -> int:
        """Run rules to a fixpoint. Returns the number of newly
        inferred triples added to ``target_graph``."""
        backend = backend if backend is not None else get_backend()
        src = _resolve_graph(source_graph, _DEFAULT_INTERNAL_GRAPH)
        tgt = _resolve_graph(target_graph, src)
        before = _backend_triple_count(backend, tgt)
        previous = before
        for _ in range(max_iterations):
            for sparql in self.rules(src, tgt):
                backend.update(sparql)
            current = _backend_triple_count(backend, tgt)
            if current == previous:
                break
            previous = current
        return _backend_triple_count(backend, tgt) - before


class CompositeReasoner(Reasoner):
    """Run several reasoners sequentially within one fixpoint envelope."""

    def __init__(self, *reasoners: Reasoner):
        if not reasoners:
            raise ValueError("CompositeReasoner requires at least one reasoner")
        self.reasoners: List[Reasoner] = list(reasoners)

    def rules(self, source_graph: URIRef, target_graph: URIRef) -> Sequence[str]:
        composite: List[str] = []
        for reasoner in self.reasoners:
            composite.extend(reasoner.rules(source_graph, target_graph))
        return composite


def _resolve_reasoner(reasoner) -> Reasoner:
    if isinstance(reasoner, Reasoner):
        return reasoner
    if reasoner is None:
        configured = getattr(settings, "DJANGORDF_REASONER", None)
        if configured is None:
            raise ImproperlyConfigured(
                "No reasoner supplied and DJANGORDF_REASONER is not set."
            )
        reasoner = configured
    if isinstance(reasoner, str):
        cls = import_string(reasoner)
        return cls()
    if isinstance(reasoner, type) and issubclass(reasoner, Reasoner):
        return reasoner()
    raise TypeError(
        f"Cannot resolve reasoner from {reasoner!r}; expected a Reasoner "
        f"instance, class, or dotted path."
    )


def materialize(
    reasoner: Optional[Union[str, Reasoner, type]] = None,
    backend=None,
    *,
    source_graph=None,
    target_graph=None,
    max_iterations: int = 50,
) -> int:
    """Programmatic entry point. Resolves ``reasoner`` from the
    argument (instance / class / dotted path) or
    ``settings.DJANGORDF_REASONER`` and runs ``materialize`` on it."""
    return _resolve_reasoner(reasoner).materialize(
        backend=backend,
        source_graph=source_graph,
        target_graph=target_graph,
        max_iterations=max_iterations,
    )
