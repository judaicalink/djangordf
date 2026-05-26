"""Default object manager bound to each RDFModel subclass.

This milestone ships only ``save`` and ``delete``. The full CRUD and
queryset API (``get``, ``all``, ``filter``, ``RDFQuerySet``) lands in
issue #8.
"""
from .conf import get_backend


def _term(term):
    return term.n3()


def _format_triple(triple):
    s, p, o = triple
    return f"{_term(s)} {_term(p)} {_term(o)} ."


class RDFManager:
    """Object manager attached to ``cls.objects`` by ``RDFModelMeta``."""

    def __init__(self, model_class):
        self.model_class = model_class
        self._backend = None

    @property
    def backend(self):
        if self._backend is None:
            self._backend = get_backend()
        return self._backend

    def save(self, instance) -> None:
        graph_iri = instance._meta.graph_iri
        iri = instance.iri
        triples = instance._to_triples()
        body = "\n".join(_format_triple(t) for t in triples)
        sparql = (
            f"WITH <{graph_iri}> "
            f"DELETE {{ <{iri}> ?p ?o }} WHERE {{ <{iri}> ?p ?o }} ;"
            f"INSERT DATA {{ GRAPH <{graph_iri}> {{ {body} }} }}"
        )
        self.backend.update(sparql)

    def delete(self, instance) -> None:
        graph_iri = instance._meta.graph_iri
        iri = instance.iri
        sparql = (
            f"WITH <{graph_iri}> "
            f"DELETE {{ <{iri}> ?p ?o }} WHERE {{ <{iri}> ?p ?o }}"
        )
        self.backend.update(sparql)
