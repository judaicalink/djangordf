"""Default object manager bound to each RDFModel subclass.

``RDFManager`` provides the Django-style ``Model.objects`` entry point:
``create``, ``get``, ``save``, ``delete``, ``all`` and ``filter``. Reads
hydrate instances by dispatching the CONSTRUCTed graph through each
property's ``from_rdf``. ``all`` and ``filter`` return a lazy
``RDFQuerySet`` that only hits the store on iteration or terminal
methods (``len``, ``count``, ``first``).
"""
from typing import List

from rdflib import BNode, Literal, URIRef

from .conf import get_backend


_FILTER_DUMMY_SUBJECT = URIRef("urn:_djangordf:_filter:dummy")


_KNOWN_LOOKUP_SUFFIXES = frozenset({
    "exact", "iexact",
    "contains", "icontains",
    "startswith", "istartswith",
    "endswith", "iendswith",
    "in",
    "gt", "gte", "lt", "lte",
    "regex", "iregex",
    "isnull",
    "year", "month", "day",
    "hour", "minute", "second",
})


def _peel_lookup_suffix(segments):
    """Return ``(path_segments, suffix)``. A suffix is peeled only when
    the key has at least two ``__``-separated segments, so a single
    attribute name that happens to collide with a suffix is still
    treated as the attribute name."""
    if len(segments) >= 2 and segments[-1] in _KNOWN_LOOKUP_SUFFIXES:
        return segments[:-1], segments[-1]
    return segments, "exact"


def _term(term):
    return term.n3()


def _format_triple(triple):
    s, p, o = triple
    return f"{_term(s)} {_term(p)} {_term(o)} ."


def _render_sparql_term(term) -> str:
    """Render a SPARQL term. ``?var`` strings pass through verbatim;
    anything else is rdflib-serialised via ``.n3()``."""
    if isinstance(term, str) and term.startswith("?"):
        return term
    return term.n3()


def _render_triple(s, p, o) -> str:
    """Render a triple pattern. Predicate is always rendered as an
    angle-bracketed IRI; subject and object go through
    :func:`_render_sparql_term`."""
    return (
        f"{_render_sparql_term(s)} "
        f"<{p}> "
        f"{_render_sparql_term(o)} ."
    )


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
        forward_sparql = (
            f"CONSTRUCT {{ <{iri}> ?p ?o }} WHERE {{ "
            f"GRAPH <{graph_iri}> {{ <{iri}> ?p ?o }} }}"
        )
        graph = self.backend.query(forward_sparql)
        if len(graph) == 0:
            raise self.model_class.DoesNotExist(str(iri))
        if self._has_reverse_properties():
            reverse_sparql = (
                f"CONSTRUCT {{ ?s ?p <{iri}> }} WHERE {{ "
                f"GRAPH <{graph_iri}> {{ ?s ?p <{iri}> }} }}"
            )
            reverse_graph = self.backend.query(reverse_sparql)
            for triple in reverse_graph:
                graph.add(triple)
        instance = self.model_class(iri=iri)
        self._hydrate(instance, graph, iri)
        return instance

    def _has_reverse_properties(self) -> bool:
        from .properties import ObjectProperty
        return any(
            isinstance(p, ObjectProperty) and p.reverse
            for p in getattr(self.model_class, "_properties", {}).values()
        )

    def _hydrate(self, instance, graph, subject) -> None:
        for attr, prop in self.model_class._properties.items():
            if prop.predicate is None:
                continue
            setattr(instance, attr, prop.from_rdf(graph, subject))

    def all(self) -> "RDFQuerySet":
        return RDFQuerySet(self)

    def filter(self, *q_args, **kwargs) -> "RDFQuerySet":
        from .query import Q
        if not q_args and not kwargs:
            return RDFQuerySet(self)
        top = Q(*q_args, **kwargs)
        return RDFQuerySet(self, q=top)

    def _emit_leaf(self, key, value, current_var, current_cls, counter):
        """Render one ``(key, value)`` filter leaf as a list of SPARQL
        pattern strings (one per triple / FILTER). ``counter`` is a
        single-element list so callers share the same monotonic
        variable-name source across the entire Q walk."""
        raw_segments = key.split("__")
        path_segments, suffix = _peel_lookup_suffix(raw_segments)
        lines: List[str] = []
        for i, segment in enumerate(path_segments):
            prop = self._resolve_segment(current_cls, segment)
            is_reverse = getattr(prop, "reverse", False)
            if i == len(path_segments) - 1:
                if suffix == "exact":
                    obj_term = self._object_term(prop, value)
                    if is_reverse:
                        lines.append(
                            _render_triple(obj_term, prop.predicate, current_var)
                        )
                    else:
                        lines.append(
                            _render_triple(current_var, prop.predicate, obj_term)
                        )
                elif suffix == "isnull":
                    counter[0] += 1
                    anon_var = f"?v{counter[0]}"
                    if is_reverse:
                        triple = _render_triple(
                            anon_var, prop.predicate, current_var,
                        )
                    else:
                        triple = _render_triple(
                            current_var, prop.predicate, anon_var,
                        )
                    if bool(value):
                        lines.append(
                            f"FILTER NOT EXISTS {{ {triple} }}"
                        )
                    else:
                        lines.append(triple)
                else:
                    counter[0] += 1
                    terminal_var = f"?v{counter[0]}"
                    if is_reverse:
                        lines.append(
                            _render_triple(terminal_var, prop.predicate, current_var)
                        )
                    else:
                        lines.append(
                            _render_triple(current_var, prop.predicate, terminal_var)
                        )
                    lines.append(
                        f"FILTER("
                        f"{self._build_filter_clause(terminal_var, suffix, value, prop)}"
                        f")"
                    )
                break
            from .properties import ObjectProperty
            if not isinstance(prop, ObjectProperty):
                raise ValueError(
                    f"non-terminal lookup segment {segment!r} on "
                    f"{current_cls.__name__} is not an ObjectProperty; "
                    f"cannot span"
                )
            counter[0] += 1
            next_var = f"?v{counter[0]}"
            if is_reverse:
                lines.append(
                    _render_triple(next_var, prop.predicate, current_var)
                )
            else:
                lines.append(
                    _render_triple(current_var, prop.predicate, next_var)
                )
            current_var = next_var
            current_cls = prop.target_class
        return lines

    def _emit_q(self, q, current_var, current_cls, counter) -> str:
        """Recursively render a ``Q`` tree as a SPARQL fragment string."""
        from .query import Q
        child_fragments: List[str] = []
        for child in q.children:
            if isinstance(child, Q):
                child_fragments.append(
                    self._emit_q(child, current_var, current_cls, counter)
                )
            else:
                key, value = child
                lines = self._emit_leaf(
                    key, value, current_var, current_cls, counter
                )
                child_fragments.append(" ".join(lines))
        if q.connector == Q.OR:
            body = " UNION ".join(
                f"{{ {f} }}" for f in child_fragments if f
            )
        else:
            body = " ".join(f for f in child_fragments if f)
        if q.negated:
            return f"FILTER NOT EXISTS {{ {body} }}"
        return body

    def _build_filter_clause(self, var, suffix, value, prop) -> str:
        """Render the SPARQL FILTER expression for a suffix lookup
        against ``var``. The expression is returned without its
        outer ``FILTER( … )`` wrapper — the queryset adds that on
        render."""
        if suffix == "iexact":
            return (
                f"LCASE(STR({var})) = LCASE({Literal(str(value)).n3()})"
            )
        if suffix == "contains":
            return f"CONTAINS(STR({var}), {Literal(str(value)).n3()})"
        if suffix == "icontains":
            return (
                f"CONTAINS(LCASE(STR({var})), "
                f"LCASE({Literal(str(value)).n3()}))"
            )
        if suffix == "startswith":
            return f"STRSTARTS(STR({var}), {Literal(str(value)).n3()})"
        if suffix == "istartswith":
            return (
                f"STRSTARTS(LCASE(STR({var})), "
                f"LCASE({Literal(str(value)).n3()}))"
            )
        if suffix == "endswith":
            return f"STRENDS(STR({var}), {Literal(str(value)).n3()})"
        if suffix == "iendswith":
            return (
                f"STRENDS(LCASE(STR({var})), "
                f"LCASE({Literal(str(value)).n3()}))"
            )
        if suffix == "in":
            try:
                items = list(value)
            except TypeError as exc:
                raise TypeError(
                    f"__in expects an iterable; got {type(value).__name__}"
                ) from exc
            rendered = ", ".join(
                self._object_term(prop, item).n3() for item in items
            )
            return f"{var} IN ({rendered})"
        if suffix == "regex":
            return f"REGEX(STR({var}), {Literal(str(value)).n3()})"
        if suffix == "iregex":
            return f"REGEX(STR({var}), {Literal(str(value)).n3()}, \"i\")"
        if suffix in {"year", "month", "day", "hour", "minute", "second"}:
            fn = {
                "year": "YEAR",
                "month": "MONTH",
                "day": "DAY",
                "hour": "HOURS",
                "minute": "MINUTES",
                "second": "SECONDS",
            }[suffix]
            return f"{fn}({var}) = {Literal(int(value)).n3()}"
        op = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}[suffix]
        return f"{var} {op} {self._object_term(prop, value).n3()}"

    @staticmethod
    def _resolve_segment(cls, segment):
        try:
            prop = cls._properties[segment]
        except KeyError as exc:
            raise ValueError(
                f"Unknown attribute {segment!r} on {cls.__name__}"
            ) from exc
        if prop.predicate is None:
            raise ValueError(
                f"Property {segment!r} on {cls.__name__} has no "
                f"predicate; cannot use it in filter()"
            )
        return prop

    def _object_term(self, prop, value):
        if isinstance(value, (URIRef, Literal, BNode)):
            return value
        from .models import RDFModel
        from .namespaces import LangString
        if isinstance(value, RDFModel) and value.iri is not None:
            return URIRef(value.iri)
        if isinstance(value, LangString):
            return Literal(value.value, lang=value.lang)
        # ``prop.to_rdf`` of a ``many=True`` property iterates over
        # ``value`` — that's wrong for filter, where the user supplied a
        # single scalar to compare against. Build a single-value triple
        # by temporarily flipping the cardinality.
        original_many = getattr(prop, "many", False)
        prop.many = False
        try:
            triples = prop.to_rdf(_FILTER_DUMMY_SUBJECT, value)
        finally:
            prop.many = original_many
        if not triples:
            raise ValueError(
                f"Cannot serialise {value!r} for property {prop.attr_name!r}"
            )
        return triples[0][2]


class RDFQuerySet:
    """Lazy queryset over an ``RDFManager``.

    Materialises on iteration / ``len`` / ``count`` / ``first`` /
    ``__getitem__(int)`` by issuing ``SELECT DISTINCT ?s`` to
    enumerate matching subjects, then calling ``manager.get(s)`` per
    subject. ``order_by`` and slicing are both chainable and lazy —
    they return new querysets carrying ``ORDER BY`` / ``LIMIT`` /
    ``OFFSET`` state that the SPARQL builder honours on next
    materialisation.
    """

    def __init__(
        self,
        manager: RDFManager,
        q=None,
        order_by: tuple = (),
        limit=None,
        offset=None,
    ):
        self._manager = manager
        self._q = q
        self._order_by = tuple(order_by)
        self._limit = limit
        self._offset = offset
        self._results_cache = None

    def _clone(self, **overrides):
        defaults = dict(
            q=self._q,
            order_by=self._order_by,
            limit=self._limit,
            offset=self._offset,
        )
        defaults.update(overrides)
        return RDFQuerySet(self._manager, **defaults)

    # -- chainable surface --------------------------------------------------

    def order_by(self, *fields):
        return self._clone(order_by=tuple(fields))

    # -- SPARQL construction ------------------------------------------------

    def _build_subject_sparql(self) -> str:
        model = self._manager.model_class
        graph_iri = model._meta.graph_iri
        class_iri = model._meta.class_iri
        counter = [0]

        parts = [f"?s a <{class_iri}> ."]
        if self._q is not None:
            fragment = self._manager._emit_q(
                self._q, "?s", model, counter,
            )
            if fragment:
                parts.append(fragment)

        select_vars = ["?s"]
        order_tokens = []
        for field in self._order_by:
            descending = field.startswith("-")
            attr = field.lstrip("-")
            prop = self._manager._resolve_segment(model, attr)
            counter[0] += 1
            ord_var = f"?ord_{counter[0]}"
            parts.append(
                _render_triple("?s", prop.predicate, ord_var)
            )
            select_vars.append(ord_var)
            order_tokens.append(
                f"DESC({ord_var})" if descending else ord_var
            )

        body = " ".join(parts)
        select = "SELECT DISTINCT " + " ".join(select_vars)
        sparql = (
            f"{select} WHERE {{ GRAPH <{graph_iri}> {{ {body} }} }}"
        )
        if order_tokens:
            sparql += " ORDER BY " + " ".join(order_tokens)
        if self._limit is not None:
            sparql += f" LIMIT {self._limit}"
        if self._offset is not None:
            sparql += f" OFFSET {self._offset}"
        return sparql

    # -- materialisation ----------------------------------------------------

    def _fetch(self):
        if self._results_cache is not None:
            return self._results_cache
        sparql = self._build_subject_sparql()
        result = self._manager.backend.query(sparql)
        subjects = list(dict.fromkeys(row[0] for row in result))
        self._results_cache = [self._manager.get(s) for s in subjects]
        return self._results_cache

    def __iter__(self):
        return iter(self._fetch())

    def __len__(self) -> int:
        return len(self._fetch())

    def count(self) -> int:
        return len(self)

    def first(self):
        items = list(self._clone(limit=1))
        return items[0] if items else None

    # -- slicing / indexing -------------------------------------------------

    def __getitem__(self, key):
        if isinstance(key, slice):
            if key.step is not None:
                raise TypeError(
                    "RDFQuerySet does not support step in slicing"
                )
            start = key.start or 0
            stop = key.stop
            if start < 0 or (stop is not None and stop < 0):
                raise IndexError(
                    "RDFQuerySet does not support negative indices"
                )
            new_offset = (self._offset or 0) + start
            if stop is None:
                new_limit = self._limit
            else:
                window = stop - start
                if window < 0:
                    window = 0
                if self._limit is not None:
                    remaining = max(self._limit - start, 0)
                    new_limit = min(window, remaining)
                else:
                    new_limit = window
            return self._clone(
                limit=new_limit,
                offset=new_offset if new_offset else None,
            )
        if isinstance(key, int):
            if key < 0:
                raise IndexError(
                    "RDFQuerySet does not support negative indices"
                )
            items = list(self[key:key + 1])
            if not items:
                raise IndexError(key)
            return items[0]
        raise TypeError(
            f"RDFQuerySet indices must be int or slice, not "
            f"{type(key).__name__}"
        )
