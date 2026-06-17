"""Track applied migrations as triples in the configured backend."""
from typing import Iterable, Set

from rdflib import Literal, URIRef


_RECORDER_GRAPH = URIRef("urn:djangordf:migrations")
_MIGRATION_TYPE = URIRef("urn:djangordf:Migration")
_RDF_TYPE = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
_DCT_CREATED = URIRef("http://purl.org/dc/terms/created")
_XSD_DATETIME = URIRef("http://www.w3.org/2001/XMLSchema#dateTime")


def _migration_iri(name: str) -> URIRef:
    return URIRef(f"urn:djangordf:migration:{name}")


class MigrationRecorder:
    """Tiny wrapper around ``backend`` that tracks applied migrations
    in a dedicated named graph."""

    def __init__(self, backend):
        self.backend = backend

    def applied(self) -> Set[str]:
        """Return the set of migration names already recorded."""
        sparql = (
            f"SELECT ?m WHERE {{ "
            f"GRAPH <{_RECORDER_GRAPH}> {{ "
            f"?m <{_RDF_TYPE}> <{_MIGRATION_TYPE}> "
            f"}} }}"
        )
        results = self.backend.query(sparql)
        prefix = "urn:djangordf:migration:"
        names: Set[str] = set()
        for row in results:
            iri = str(row[0])
            if iri.startswith(prefix):
                names.add(iri[len(prefix):])
        return names

    def record(self, name: str, *, when: str) -> None:
        """Persist that ``name`` has been applied at ``when`` (an
        ISO-8601 timestamp). ``when`` is provided by the caller so the
        executor can stamp every applied migration with the same
        run-wide timestamp if desired."""
        iri = _migration_iri(name)
        triples = [
            (iri, _RDF_TYPE, _MIGRATION_TYPE),
            (iri, _DCT_CREATED, Literal(when, datatype=_XSD_DATETIME)),
        ]
        self.backend.add(triples, graph=_RECORDER_GRAPH)

    def forget(self, name: str) -> None:
        """Strip the record for ``name`` from the graph (used in
        tests; no production command depends on this)."""
        iri = _migration_iri(name)
        self.backend.update(
            f"WITH <{_RECORDER_GRAPH}> "
            f"DELETE {{ <{iri}> ?p ?o }} "
            f"WHERE {{ <{iri}> ?p ?o }}"
        )

    def forget_all(self, names: Iterable[str]) -> None:
        for name in names:
            self.forget(name)
