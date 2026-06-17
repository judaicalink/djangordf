"""SKOS-specific reasoner.

Propagates ``skos:broader`` / ``skos:narrower`` to their transitive
variants and closes the transitive predicates under composition.
Also enforces ``skos:exactMatch`` symmetry.
"""
from typing import Sequence

from rdflib import URIRef

from .base import Reasoner


_SKOS = "http://www.w3.org/2004/02/skos/core#"
_BROADER = _SKOS + "broader"
_NARROWER = _SKOS + "narrower"
_BROADER_TRANS = _SKOS + "broaderTransitive"
_NARROWER_TRANS = _SKOS + "narrowerTransitive"
_EXACT_MATCH = _SKOS + "exactMatch"


def _rule(template: str, src: URIRef, tgt: URIRef) -> str:
    return template.format(src=src, tgt=tgt)


class SKOSReasoner(Reasoner):
    """Run SKOS entailment rules to a fixpoint."""

    _BROADER_TO_TRANSITIVE = (
        "INSERT {{ GRAPH <{tgt}> {{ ?a <" + _BROADER_TRANS + "> ?b }} }} "
        "WHERE {{ GRAPH <{src}> {{ "
        "?a <" + _BROADER + "> ?b . "
        "}} "
        "FILTER NOT EXISTS {{ GRAPH <{tgt}> {{ "
        "?a <" + _BROADER_TRANS + "> ?b "
        "}} }} }}"
    )

    _BROADER_TRANSITIVE_CLOSURE = (
        "INSERT {{ GRAPH <{tgt}> {{ ?a <" + _BROADER_TRANS + "> ?c }} }} "
        "WHERE {{ GRAPH <{src}> {{ "
        "?a <" + _BROADER_TRANS + "> ?b . "
        "?b <" + _BROADER_TRANS + "> ?c . "
        "}} "
        "FILTER (?a != ?c) "
        "FILTER NOT EXISTS {{ GRAPH <{tgt}> {{ "
        "?a <" + _BROADER_TRANS + "> ?c "
        "}} }} }}"
    )

    _NARROWER_TO_TRANSITIVE = (
        "INSERT {{ GRAPH <{tgt}> {{ ?a <" + _NARROWER_TRANS + "> ?b }} }} "
        "WHERE {{ GRAPH <{src}> {{ "
        "?a <" + _NARROWER + "> ?b . "
        "}} "
        "FILTER NOT EXISTS {{ GRAPH <{tgt}> {{ "
        "?a <" + _NARROWER_TRANS + "> ?b "
        "}} }} }}"
    )

    _NARROWER_TRANSITIVE_CLOSURE = (
        "INSERT {{ GRAPH <{tgt}> {{ ?a <" + _NARROWER_TRANS + "> ?c }} }} "
        "WHERE {{ GRAPH <{src}> {{ "
        "?a <" + _NARROWER_TRANS + "> ?b . "
        "?b <" + _NARROWER_TRANS + "> ?c . "
        "}} "
        "FILTER (?a != ?c) "
        "FILTER NOT EXISTS {{ GRAPH <{tgt}> {{ "
        "?a <" + _NARROWER_TRANS + "> ?c "
        "}} }} }}"
    )

    _EXACT_MATCH_SYMMETRY = (
        "INSERT {{ GRAPH <{tgt}> {{ ?b <" + _EXACT_MATCH + "> ?a }} }} "
        "WHERE {{ GRAPH <{src}> {{ "
        "?a <" + _EXACT_MATCH + "> ?b . "
        "}} "
        "FILTER (?a != ?b) "
        "FILTER NOT EXISTS {{ GRAPH <{tgt}> {{ "
        "?b <" + _EXACT_MATCH + "> ?a "
        "}} }} }}"
    )

    def rules(self, source_graph: URIRef, target_graph: URIRef) -> Sequence[str]:
        return [
            _rule(self._BROADER_TO_TRANSITIVE, source_graph, target_graph),
            _rule(self._BROADER_TRANSITIVE_CLOSURE, source_graph, target_graph),
            _rule(self._NARROWER_TO_TRANSITIVE, source_graph, target_graph),
            _rule(self._NARROWER_TRANSITIVE_CLOSURE, source_graph, target_graph),
            _rule(self._EXACT_MATCH_SYMMETRY, source_graph, target_graph),
        ]
