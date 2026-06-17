"""Pluggable reasoner layer.

Materialise inferred triples into the configured backend. Pick a
reasoner via ``settings.DJANGORDF_REASONER`` (dotted import path) or
pass one directly to :func:`materialize`. Built-in reasoners cover
RDFS and SKOS; an optional :class:`OWLRLReasoner` wraps the
third-party ``owlrl`` library when installed.
"""
from .base import (
    CompositeReasoner,
    Reasoner,
    materialize,
)
from .rdfs import RDFSReasoner
from .skos import SKOSReasoner

try:  # pragma: no cover - import-time fallback
    from .owlrl import OWLRLReasoner
except ImportError:  # pragma: no cover
    OWLRLReasoner = None  # type: ignore[assignment]


__all__ = [
    "CompositeReasoner",
    "OWLRLReasoner",
    "RDFSReasoner",
    "Reasoner",
    "SKOSReasoner",
    "materialize",
]
