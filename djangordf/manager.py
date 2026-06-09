"""Default object manager bound to each RDFModel subclass.

``RDFManager`` provides the Django-style ``Model.objects`` entry point:
``create``, ``get``, ``save``, ``delete``, ``all`` and ``filter``. Reads
hydrate instances by dispatching the CONSTRUCTed graph through each
property's ``from_rdf``. ``all`` and ``filter`` return a lazy
``RDFQuerySet`` that only hits the store on iteration or terminal
methods (``len``, ``count``, ``first``).
"""
from typing import List, Tuple

from rdflib import BNode, Literal, URIRef

from .conf import get_backend


_FILTER_DUMMY_SUBJECT = URIRef("urn:_djangordf:_filter:dummy")


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

    # -- write side ---------------------------------------------------------

    def create(self, **kwargs):
        instance = self.model_class(**kwargs)
        instance.save()
        return instance

    def save(self, instance) -> None:
        graph_iri = instance._meta.graph_iri
        iri = instance.iri

        triples = list(instance._to_triples())
        mirror_triples, inverse_predicates = self._mirror_writes(instance)
        triples.extend(mirror_triples)
        body = "\n".join(_format_triple(t) for t in triples)

        statements = [
            f"WITH <{graph_iri}> "
            f"DELETE {{ <{iri}> ?p ?o }} WHERE {{ <{iri}> ?p ?o }}"
        ]
        for inv_pred in inverse_predicates:
            statements.append(
                f"WITH <{graph_iri}> "
                f"DELETE {{ ?s <{inv_pred}> <{iri}> }} "
                f"WHERE {{ ?s <{inv_pred}> <{iri}> }}"
            )
        statements.append(
            f"INSERT DATA {{ GRAPH <{graph_iri}> {{ {body} }} }}"
        )
        self.backend.update(" ;".join(statements))

    def delete(self, instance) -> None:
        graph_iri = instance._meta.graph_iri
        iri = instance.iri
        statements = [
            f"WITH <{graph_iri}> "
            f"DELETE {{ <{iri}> ?p ?o }} WHERE {{ <{iri}> ?p ?o }}"
        ]
        for inv_pred in self._inverse_predicates(instance):
            statements.append(
                f"WITH <{graph_iri}> "
                f"DELETE {{ ?s <{inv_pred}> <{iri}> }} "
                f"WHERE {{ ?s <{inv_pred}> <{iri}> }}"
            )
        self.backend.update(" ;".join(statements))

    def _inverse_properties(self, instance):
        """Yield ``(prop, inverse_predicate)`` for every ObjectProperty
        on this model that declares an ``inverse=``."""
        from .properties import ObjectProperty
        properties = getattr(self.model_class, "_properties", None) or {}
        for prop in properties.values():
            if not isinstance(prop, ObjectProperty) or prop.inverse is None:
                continue
            inv_pred = prop.inverse_predicate
            if inv_pred is None:
                continue
            yield prop, inv_pred

    def _inverse_predicates(self, instance):
        """Distinct inverse predicates declared on this model."""
        seen = []
        for _, inv_pred in self._inverse_properties(instance):
            if inv_pred not in seen:
                seen.append(inv_pred)
        return seen

    def _mirror_writes(self, instance):
        """Build the mirror triples and the inverse-predicate list for
        ``instance``. The triples flow into the INSERT DATA body; the
        predicates drive the extra DELETE statements that strip stale
        mirror triples on the (potentially different) target subjects."""
        mirror_triples = []
        inverse_predicates = []
        for prop, inv_pred in self._inverse_properties(instance):
            if inv_pred not in inverse_predicates:
                inverse_predicates.append(inv_pred)
            value = getattr(instance, prop.attr_name, None)
            if value is None:
                continue
            if prop.many:
                targets = value
            else:
                targets = [value]
            for target in targets:
                target_iri = self._iri_of_value(target)
                mirror_triples.append((target_iri, inv_pred, instance.iri))
        return mirror_triples, inverse_predicates

    @staticmethod
    def _iri_of_value(value):
        if isinstance(value, URIRef):
            return value
        return URIRef(value.iri)

    # -- read side ----------------------------------------------------------

    def get(self, iri):
        iri = URIRef(iri)
        graph_iri = self.model_class._meta.graph_iri
        sparql = (
            f"CONSTRUCT {{ <{iri}> ?p ?o }} WHERE {{ "
            f"GRAPH <{graph_iri}> {{ <{iri}> ?p ?o }} }}"
        )
        graph = self.backend.query(sparql)
        if len(graph) == 0:
            raise self.model_class.DoesNotExist(str(iri))
        instance = self.model_class(iri=iri)
        self._hydrate(instance, graph, iri)
        return instance

    def _hydrate(self, instance, graph, subject) -> None:
        for attr, prop in self.model_class._properties.items():
            if prop.predicate is None:
                continue
            setattr(instance, attr, prop.from_rdf(graph, subject))

    def all(self) -> "RDFQuerySet":
        return RDFQuerySet(self, [])

    def filter(self, **kwargs) -> "RDFQuerySet":
        triple_patterns: List[Tuple[URIRef, object]] = []
        for attr, value in kwargs.items():
            if attr not in self.model_class._properties:
                raise ValueError(
                    f"Unknown attribute on "
                    f"{self.model_class.__name__}: {attr!r}"
                )
            prop = self.model_class._properties[attr]
            if prop.predicate is None:
                raise ValueError(
                    f"Property {attr!r} has no predicate; "
                    f"cannot use it in filter()"
                )
            triple_patterns.append((prop.predicate, self._object_term(prop, value)))
        return RDFQuerySet(self, triple_patterns)

    def _object_term(self, prop, value):
        if isinstance(value, (URIRef, Literal, BNode)):
            return value
        from .models import RDFModel
        if isinstance(value, RDFModel) and value.iri is not None:
            return URIRef(value.iri)
        triples = prop.to_rdf(_FILTER_DUMMY_SUBJECT, value)
        if not triples:
            raise ValueError(
                f"Cannot serialise {value!r} for property {prop.attr_name!r}"
            )
        return triples[0][2]


class RDFQuerySet:
    """Lazy queryset over an ``RDFManager``.

    Materialises on iteration / ``len`` / ``count`` / ``first`` by
    issuing ``SELECT DISTINCT ?s`` to enumerate matching subjects, then
    calling ``manager.get(s)`` per subject. Each subject is therefore
    fetched in a separate CONSTRUCT — clear and correct for the walking
    skeleton; an N+1 collapse can be a later optimisation.
    """

    def __init__(self, manager: RDFManager, triple_patterns):
        self._manager = manager
        self._triple_patterns = list(triple_patterns)
        self._results_cache = None

    def _build_subject_sparql(self) -> str:
        model = self._manager.model_class
        graph_iri = model._meta.graph_iri
        class_iri = model._meta.class_iri
        patterns = [f"?s a <{class_iri}> ."]
        for predicate, obj_term in self._triple_patterns:
            patterns.append(f"?s <{predicate}> {obj_term.n3()} .")
        body = " ".join(patterns)
        return (
            f"SELECT DISTINCT ?s WHERE {{ "
            f"GRAPH <{graph_iri}> {{ {body} }} }}"
        )

    def _fetch(self):
        if self._results_cache is not None:
            return self._results_cache
        sparql = self._build_subject_sparql()
        result = self._manager.backend.query(sparql)
        subjects = [row[0] for row in result]
        self._results_cache = [self._manager.get(s) for s in subjects]
        return self._results_cache

    def __iter__(self):
        return iter(self._fetch())

    def __len__(self) -> int:
        return len(self._fetch())

    def count(self) -> int:
        return len(self)

    def first(self):
        items = self._fetch()
        return items[0] if items else None
