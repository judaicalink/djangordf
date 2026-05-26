"""SPARQL 1.1 HTTP triple-store backend for Apache Jena Fuseki and similar."""
import re
from io import BytesIO
from typing import Optional

import requests
from rdflib import Graph
from rdflib.query import Result

from .base import TripleStoreBackend


class FusekiBackend(TripleStoreBackend):
    """Triple-store backend that talks SPARQL 1.1 HTTP to a remote endpoint.

    Compatible with Apache Jena Fuseki and any other store that implements
    the SPARQL 1.1 Protocol (Blazegraph, GraphDB, Stardog).
    """

    _QUERY_FORMS = ("CONSTRUCT", "DESCRIBE", "SELECT", "ASK")

    def __init__(
        self,
        endpoint: str,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.session = requests.Session()
        if user is not None and password is not None:
            self.session.auth = (user, password)

    def query(self, sparql):
        form = self._detect_query_form(sparql)
        if form in ("CONSTRUCT", "DESCRIBE"):
            accept = "text/turtle"
        else:
            accept = "application/sparql-results+json"
        response = self._post(
            f"{self.endpoint}/query",
            sparql,
            content_type="application/sparql-query",
            accept=accept,
        )
        if form in ("CONSTRUCT", "DESCRIBE"):
            graph = Graph()
            graph.parse(data=response.text, format="turtle")
            return graph
        return Result.parse(BytesIO(response.content), format="json")

    def update(self, sparql):
        self._post(
            f"{self.endpoint}/update",
            sparql,
            content_type="application/sparql-update",
            accept="*/*",
        )

    def add(self, triples, graph=None):
        raise NotImplementedError

    def remove(self, pattern, graph=None):
        raise NotImplementedError

    def clear(self, graph=None):
        raise NotImplementedError

    def _post(self, url, body, content_type, accept):
        response = self.session.post(
            url,
            data=body,
            headers={
                "Content-Type": content_type,
                "Accept": accept,
            },
        )
        response.raise_for_status()
        return response

    @classmethod
    def _detect_query_form(cls, sparql):
        """Pick the first SPARQL query keyword that appears in the string,
        ignoring SPARQL comments."""
        cleaned = re.sub(r"#[^\n]*", "", sparql).upper()
        for keyword in cls._QUERY_FORMS:
            if re.search(rf"\b{keyword}\b", cleaned):
                return keyword
        raise ValueError("Cannot determine SPARQL query form")
