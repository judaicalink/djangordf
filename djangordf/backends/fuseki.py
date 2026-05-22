"""SPARQL 1.1 HTTP triple-store backend for Apache Jena Fuseki and similar."""
from typing import Optional

import requests

from .base import TripleStoreBackend


class FusekiBackend(TripleStoreBackend):
    """Triple-store backend that talks SPARQL 1.1 HTTP to a remote endpoint.

    Compatible with Apache Jena Fuseki and any other store that implements
    the SPARQL 1.1 Protocol (Blazegraph, GraphDB, Stardog).
    """

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
        raise NotImplementedError

    def update(self, sparql):
        raise NotImplementedError

    def add(self, triples, graph=None):
        raise NotImplementedError

    def remove(self, pattern, graph=None):
        raise NotImplementedError

    def clear(self, graph=None):
        raise NotImplementedError
