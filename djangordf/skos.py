"""SKOS class IRI, CURIE resolution, and convention-predicate map.

The CURIE resolver delegates to the module-level
:data:`djangordf.namespaces.registry` so there is exactly one place
that knows how to turn ``"skos:Concept"`` into a ``URIRef``.

``DEFAULT_PREDICATES`` is the convention map consulted by
``RDFModelMeta`` when a ``Property`` is declared without an explicit
``predicate=`` — it lets users write ``pref_label = LangStringProperty()``
and have the metaclass wire it to ``skos:prefLabel`` automatically.
"""
from typing import Dict

from rdflib import URIRef
from rdflib.namespace import SKOS

from .namespaces import registry


Concept = SKOS.Concept


DEFAULT_PREDICATES: Dict[str, URIRef] = {
    "pref_label": SKOS.prefLabel,
    "alt_label": SKOS.altLabel,
    "hidden_label": SKOS.hiddenLabel,
    "definition": SKOS.definition,
    "note": SKOS.note,
    "broader": SKOS.broader,
    "narrower": SKOS.narrower,
    "related": SKOS.related,
    "exact_match": SKOS.exactMatch,
    "close_match": SKOS.closeMatch,
    "in_scheme": SKOS.inScheme,
}


def resolve_curie(value) -> URIRef:
    """Turn a CURIE or full IRI into a ``URIRef`` via the registry.

    Kept as a top-level helper for callers that just want the function
    without holding a reference to the registry.
    """
    return registry.resolve(value)
