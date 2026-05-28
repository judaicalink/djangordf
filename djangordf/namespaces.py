"""Namespace utilities for djangordf.

Holds the ``LangString`` dataclass (used by ``LangStringProperty``)
and the process-wide ``NamespaceRegistry`` — a thin wrapper over
rdflib namespaces that gives users a single place to register prefix
bindings and a single ``resolve()`` that converts CURIEs into
``URIRef`` objects.
"""
from dataclasses import dataclass
from typing import Dict, Union

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import DCTERMS, FOAF, OWL, RDF, RDFS, SKOS, XSD


@dataclass(frozen=True)
class LangString:
    """A language-tagged literal, paired with a BCP 47 language tag.

    Used by ``LangStringProperty`` to round-trip ``rdf:langString``
    values cleanly between Python and the triple store.
    """

    value: str
    lang: str


_FULL_IRI_PREFIXES = ("http://", "https://", "urn:")


_DEFAULT_BINDINGS: Dict[str, Namespace] = {
    "rdf": Namespace(str(RDF)),
    "rdfs": Namespace(str(RDFS)),
    "owl": Namespace(str(OWL)),
    "xsd": Namespace(str(XSD)),
    "skos": Namespace(str(SKOS)),
    "dct": Namespace(str(DCTERMS)),
    "foaf": Namespace(str(FOAF)),
}


class NamespaceRegistry:
    """Per-process registry of prefix -> namespace bindings.

    Seeded with the common RDF/OWL/SKOS/Dublin Core/FOAF prefixes;
    extended through :py:meth:`register` (typically from
    ``settings.DJANGORDF_NAMESPACES`` via ``apply_namespace_settings``).
    """

    def __init__(self) -> None:
        self._bindings: Dict[str, Namespace] = dict(_DEFAULT_BINDINGS)

    def register(self, prefix: str, uri: Union[str, Namespace]) -> None:
        """Add or overwrite a prefix binding.

        Raw strings are wrapped in ``rdflib.Namespace`` so concatenation
        produces ``URIRef`` objects with no extra ceremony.
        """
        if not isinstance(uri, Namespace):
            uri = Namespace(str(uri))
        self._bindings[prefix] = uri

    def bindings(self) -> Dict[str, Namespace]:
        """Snapshot of current prefix -> namespace bindings."""
        return dict(self._bindings)

    def bind_to_graph(self, graph: Graph) -> None:
        """Bind every prefix in this registry on ``graph`` so its
        Turtle output uses pretty prefixes instead of full IRIs."""
        for prefix, ns in self._bindings.items():
            graph.bind(prefix, ns, override=True)

    def resolve(self, value) -> URIRef:
        """Turn a CURIE (``"skos:Concept"``) or a full IRI into a
        ``URIRef``. Full IRIs pass straight through. Unknown prefixes
        raise ``ValueError`` so misconfiguration is loud."""
        if isinstance(value, URIRef):
            return value
        if not isinstance(value, str):
            raise TypeError(f"Cannot resolve {value!r} as CURIE or IRI")

        if value.startswith(_FULL_IRI_PREFIXES):
            return URIRef(value)
        if ":" in value:
            prefix, local = value.split(":", 1)
            if prefix in self._bindings:
                return URIRef(self._bindings[prefix] + local)
            raise ValueError(f"Unknown CURIE prefix: {prefix!r}")
        return URIRef(value)


registry = NamespaceRegistry()


def apply_namespace_settings(extra: Union[Dict[str, str], None] = None) -> None:
    """Feed ``settings.DJANGORDF_NAMESPACES`` (or the ``extra`` dict for
    tests) into the module-level :data:`registry`.

    Safe to call before Django is configured: if settings access raises
    ``ImproperlyConfigured`` and no explicit ``extra`` was given, this
    is a no-op.
    """
    if extra is None:
        try:
            from django.conf import settings
            extra = getattr(settings, "DJANGORDF_NAMESPACES", {})
        except Exception:
            return
    for prefix, uri in (extra or {}).items():
        registry.register(prefix, uri)
