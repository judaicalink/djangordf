"""Canonical RDFS reasoner.

Five rules covering ``rdfs:subClassOf`` transitivity, type
propagation through ``subClassOf`` / ``subPropertyOf``, and ``domain``
/ ``range`` inference. Implemented as SPARQL ``INSERT-WHERE``
templates so they execute against any SPARQL 1.1 backend.
"""
from typing import Sequence

from rdflib import URIRef

from .base import Reasoner


_RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
_RDFS_SUBCLASS_OF = "http://www.w3.org/2000/01/rdf-schema#subClassOf"
_RDFS_SUBPROP_OF = "http://www.w3.org/2000/01/rdf-schema#subPropertyOf"
_RDFS_DOMAIN = "http://www.w3.org/2000/01/rdf-schema#domain"
_RDFS_RANGE = "http://www.w3.org/2000/01/rdf-schema#range"


def _rule(template: str, src: URIRef, tgt: URIRef) -> str:
    return template.format(src=src, tgt=tgt)


class RDFSReasoner(Reasoner):
    """Run canonical RDFS entailment rules to a fixpoint."""

    _SUBCLASS_TRANSITIVE = (
        "INSERT {{ GRAPH <{tgt}> {{ ?a <" + _RDFS_SUBCLASS_OF + "> ?c }} }} "
        "WHERE {{ GRAPH <{src}> {{ "
        "?a <" + _RDFS_SUBCLASS_OF + "> ?b . "
        "?b <" + _RDFS_SUBCLASS_OF + "> ?c . "
        "}} "
        "FILTER (?a != ?c) "
        "FILTER NOT EXISTS {{ GRAPH <{tgt}> {{ "
        "?a <" + _RDFS_SUBCLASS_OF + "> ?c "
        "}} }} }}"
    )

    _TYPE_VIA_SUBCLASS = (
        "INSERT {{ GRAPH <{tgt}> {{ ?s <" + _RDF_TYPE + "> ?y }} }} "
        "WHERE {{ GRAPH <{src}> {{ "
        "?s <" + _RDF_TYPE + "> ?x . "
        "?x <" + _RDFS_SUBCLASS_OF + "> ?y . "
        "}} "
        "FILTER NOT EXISTS {{ GRAPH <{tgt}> {{ "
        "?s <" + _RDF_TYPE + "> ?y "
        "}} }} }}"
    )

    _SUBPROP_TRANSITIVE = (
        "INSERT {{ GRAPH <{tgt}> {{ ?s ?q ?o }} }} "
        "WHERE {{ GRAPH <{src}> {{ "
        "?p <" + _RDFS_SUBPROP_OF + "> ?q . "
        "?s ?p ?o . "
        "}} "
        "FILTER NOT EXISTS {{ GRAPH <{tgt}> {{ ?s ?q ?o }} }} }}"
    )

    _DOMAIN_INFERENCE = (
        "INSERT {{ GRAPH <{tgt}> {{ ?s <" + _RDF_TYPE + "> ?d }} }} "
        "WHERE {{ GRAPH <{src}> {{ "
        "?p <" + _RDFS_DOMAIN + "> ?d . "
        "?s ?p ?o . "
        "}} "
        "FILTER NOT EXISTS {{ GRAPH <{tgt}> {{ "
        "?s <" + _RDF_TYPE + "> ?d "
        "}} }} }}"
    )

    _RANGE_INFERENCE = (
        "INSERT {{ GRAPH <{tgt}> {{ ?o <" + _RDF_TYPE + "> ?r }} }} "
        "WHERE {{ GRAPH <{src}> {{ "
        "?p <" + _RDFS_RANGE + "> ?r . "
        "?s ?p ?o . "
        "}} "
        "FILTER (isIRI(?o) || isBlank(?o)) "
        "FILTER NOT EXISTS {{ GRAPH <{tgt}> {{ "
        "?o <" + _RDF_TYPE + "> ?r "
        "}} }} }}"
    )

    def rules(self, source_graph: URIRef, target_graph: URIRef) -> Sequence[str]:
        return [
            _rule(self._SUBCLASS_TRANSITIVE, source_graph, target_graph),
            _rule(self._TYPE_VIA_SUBCLASS, source_graph, target_graph),
            _rule(self._SUBPROP_TRANSITIVE, source_graph, target_graph),
            _rule(self._DOMAIN_INFERENCE, source_graph, target_graph),
            _rule(self._RANGE_INFERENCE, source_graph, target_graph),
        ]
