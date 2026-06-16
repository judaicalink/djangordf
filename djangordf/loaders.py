"""Read-only loaders for external SKOS vocabularies.

The generic :func:`load_skos` accepts an HTTP/HTTPS URL, a filesystem
path, or an in-memory ``rdflib.Graph``, parses it into a graph, and
writes the triples into the configured triple store under a dedicated
"external" named graph. Format detection falls back through an
explicit ``format=`` argument, the HTTP ``Content-Type``, and the URL
extension.

The optional :func:`load_external_concept` is a thin wrapper that
issues an HTTP GET with content-negotiation headers, intended for
dereferencing a single SKOS / GND / AAT / Wikidata IRI.
"""
from typing import Optional, Union

import requests
from django.core.exceptions import ImproperlyConfigured
from rdflib import Graph, URIRef

from .conf import get_backend


_DEFAULT_EXTERNAL_GRAPH = URIRef("urn:djangordf:external")


_ACCEPT_HEADER = (
    "text/turtle, "
    "application/rdf+xml;q=0.9, "
    "application/ld+json;q=0.8, "
    "application/n-triples;q=0.7"
)


_MIME_FORMATS = {
    "text/turtle": "turtle",
    "application/x-turtle": "turtle",
    "application/rdf+xml": "xml",
    "text/rdf+xml": "xml",
    "application/xml": "xml",
    "application/ld+json": "json-ld",
    "application/json": "json-ld",
    "application/n-triples": "nt",
    "text/plain": "nt",
    "application/n-quads": "nquads",
}


_EXTENSION_FORMATS = {
    ".ttl": "turtle",
    ".turtle": "turtle",
    ".n3": "n3",
    ".rdf": "xml",
    ".xml": "xml",
    ".owl": "xml",
    ".jsonld": "json-ld",
    ".json": "json-ld",
    ".nt": "nt",
    ".nq": "nquads",
}


def _default_external_graph_iri() -> URIRef:
    """Resolve the configured external graph IRI without forcing
    Django settings to load when no environment is configured."""
    try:
        from django.conf import settings
        configured = getattr(settings, "DJANGORDF_EXTERNAL_GRAPH", None)
    except ImproperlyConfigured:
        configured = None
    if configured is None:
        return _DEFAULT_EXTERNAL_GRAPH
    return URIRef(configured)


def _format_from_mime(mime: Optional[str]) -> Optional[str]:
    if not mime:
        return None
    primary = mime.split(";", 1)[0].strip().lower()
    return _MIME_FORMATS.get(primary)


def _format_from_path(path: str) -> Optional[str]:
    lowered = path.lower()
    for ext, fmt in _EXTENSION_FORMATS.items():
        if lowered.endswith(ext):
            return fmt
    return None


def _is_http_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def _parse_source(source, *, format=None) -> Graph:
    """Build an in-memory ``rdflib.Graph`` from any supported source."""
    if isinstance(source, Graph):
        clone = Graph()
        for triple in source:
            clone.add(triple)
        return clone
    if not isinstance(source, str):
        raise TypeError(
            f"load_skos expected a URL, path, or rdflib.Graph; "
            f"got {type(source).__name__}"
        )

    graph = Graph()
    if _is_http_url(source):
        response = requests.get(
            source, headers={"Accept": _ACCEPT_HEADER},
        )
        response.raise_for_status()
        inferred = (
            format
            or _format_from_mime(response.headers.get("Content-Type"))
            or _format_from_path(source)
        )
        graph.parse(data=response.text, format=inferred)
    else:
        inferred = format or _format_from_path(source)
        graph.parse(source, format=inferred)
    return graph


def load_skos(
    source,
    *,
    backend=None,
    graph: Optional[Union[str, URIRef]] = None,
    format: Optional[str] = None,
) -> int:
    """Load triples from ``source`` into the configured backend.

    ``source`` may be a filesystem path, an HTTP/HTTPS URL, or an
    in-memory ``rdflib.Graph`` instance. Returns the number of
    triples written. Triples are inserted into the configured
    external graph (``settings.DJANGORDF_EXTERNAL_GRAPH``, default
    ``urn:djangordf:external``) unless ``graph=`` overrides it. The
    write goes through ``backend.add`` so backend-specific bulk
    handling applies.
    """
    parsed = _parse_source(source, format=format)
    target_backend = backend if backend is not None else get_backend()
    target_graph = (
        URIRef(graph) if graph is not None else _default_external_graph_iri()
    )
    triples = list(parsed)
    target_backend.add(triples, graph=target_graph)
    return len(triples)


def load_external_concept(
    iri: Union[str, URIRef],
    *,
    backend=None,
    graph: Optional[Union[str, URIRef]] = None,
) -> int:
    """Dereference a single concept IRI over HTTP and load the
    response into the backend. Thin wrapper around :func:`load_skos`
    that always speaks HTTP content negotiation."""
    return load_skos(str(iri), backend=backend, graph=graph)
