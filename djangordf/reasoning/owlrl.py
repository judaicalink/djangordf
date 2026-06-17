"""Optional wrapper around the third-party ``owlrl`` library.

Importing this module without ``owlrl`` installed raises
:class:`ImportError`; the :func:`materialize` method also raises
:class:`ImproperlyConfigured` with an install hint if the import
fails late.
"""
from typing import Optional

from django.core.exceptions import ImproperlyConfigured
from rdflib import Graph, URIRef

from .base import Reasoner, _backend_triple_count, _resolve_graph


try:  # pragma: no cover - exercised when owlrl is installed
    import owlrl  # type: ignore[import-untyped]
    _HAS_OWLRL = True
except ImportError:  # pragma: no cover
    owlrl = None
    _HAS_OWLRL = False


class OWLRLReasoner(Reasoner):
    """Materialise via the ``owlrl`` library's OWL-RL closure.

    The reasoner loads the source graph into an in-memory
    ``rdflib.Graph``, runs the OWL-RL closure, and writes the *new*
    triples back into the target graph through the backend.
    """

    def __init__(self, profile: Optional[object] = None):
        if not _HAS_OWLRL:
            raise ImproperlyConfigured(
                "OWLRLReasoner requires the 'owlrl' package; "
                "install it with `pip install owlrl`."
            )
        self.profile = profile or owlrl.OWLRL_Semantics

    def materialize(
        self,
        backend=None,
        *,
        source_graph=None,
        target_graph=None,
        max_iterations: int = 50,
    ) -> int:
        from ..conf import get_backend
        backend = backend if backend is not None else get_backend()
        src = _resolve_graph(
            source_graph, URIRef("urn:djangordf:default"),
        )
        tgt = _resolve_graph(target_graph, src)

        before_count = _backend_triple_count(backend, tgt)

        # Pull the source graph into memory.
        source_dump = backend.query(
            "CONSTRUCT { ?s ?p ?o } WHERE { "
            f"GRAPH <{src}> {{ ?s ?p ?o }} }}"
        )
        graph = Graph()
        for triple in source_dump:
            graph.add(triple)

        # Snapshot existing triples in the target so we can compute
        # the delta even when target != source.
        existing = set()
        if tgt != src:
            target_dump = backend.query(
                "CONSTRUCT { ?s ?p ?o } WHERE { "
                f"GRAPH <{tgt}> {{ ?s ?p ?o }} }}"
            )
            for triple in target_dump:
                existing.add(triple)
        else:
            existing = set(graph)

        owlrl.DeductiveClosure(self.profile).expand(graph)

        new_triples = [t for t in graph if t not in existing]
        if new_triples:
            backend.add(new_triples, graph=tgt)

        return _backend_triple_count(backend, tgt) - before_count
