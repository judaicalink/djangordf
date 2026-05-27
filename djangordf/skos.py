"""SKOS class IRI and CURIE resolution for the RDFModel default meta.

A full ``NamespaceRegistry`` is implemented in issue #9; this module
ships only the constants the metaclass and ``_build_meta`` need so #6
can be merged on its own.
"""
from rdflib import URIRef
from rdflib.namespace import RDF, RDFS, SKOS, XSD


Concept = SKOS.Concept


_CURIE_TABLE = {
    "skos": SKOS,
    "rdf": RDF,
    "rdfs": RDFS,
    "xsd": XSD,
}


def resolve_curie(value) -> URIRef:
    """Turn a CURIE (``skos:Concept``) or a full IRI into a ``URIRef``.

    Full IRIs (``http://``, ``https://``, ``urn:``) pass straight
    through. Unknown prefixes raise ``ValueError`` so misconfiguration
    is loud.
    """
    if isinstance(value, URIRef):
        return value
    if not isinstance(value, str):
        raise TypeError(f"Cannot resolve {value!r} as CURIE or IRI")

    if value.startswith(("http://", "https://", "urn:")):
        return URIRef(value)
    if ":" in value:
        prefix, local = value.split(":", 1)
        if prefix in _CURIE_TABLE:
            return URIRef(_CURIE_TABLE[prefix] + local)
        raise ValueError(f"Unknown CURIE prefix: {prefix!r}")
    return URIRef(value)
