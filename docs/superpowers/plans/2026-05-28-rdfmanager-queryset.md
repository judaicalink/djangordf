# RDFManager and RDFQuerySet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Round out `RDFManager` with `create`, `get`, `all`, `filter`, and a lazy `RDFQuerySet`. After this, `Model.objects.create(...).save()` → `Model.objects.get(iri)` roundtrips every declared property value through `prop.to_rdf` / `prop.from_rdf`, and `Model.objects.filter(...)` returns a queryset that materialises only on iteration / `len()` / `count()` / `first()`. Closes GitHub issue #8.

**Architecture:** `RDFManager` keeps its current `save` / `delete` semantics and adds three CRUD entry points and a tiny SPARQL term helper. `get(iri)` runs `CONSTRUCT { <iri> ?p ?o } WHERE { GRAPH <g> { <iri> ?p ?o } }`, raises `model_class.DoesNotExist` on an empty graph, otherwise instantiates the model and dispatches each property's slice of the graph through `prop.from_rdf(graph, subject)`. `all()` and `filter(**kwargs)` return an `RDFQuerySet` carrying the model class and a list of `(predicate, object_term)` filter patterns. The queryset is lazy: it builds a `SELECT DISTINCT ?s WHERE { GRAPH <g> { ?s a <class_iri> . [filters] } }` to enumerate matching subject IRIs and calls `manager.get(s)` for each, caching the result list. This is deliberately N+1 — clarity over premature optimisation in the walking skeleton; a single-CONSTRUCT-with-client-grouping rewrite is a follow-up if profiling demands it.

**Filter argument coercion:** `filter(<attr>=<value>)` looks up the predicate via `model_class._properties[attr].predicate`. If `value` is already a `URIRef`/`Literal`/`BNode`, it's used as-is. If the attribute is an `ObjectProperty` and `value` has an `.iri`, that IRI is used. Otherwise the property's own `to_rdf(<dummy>, value)` is called and the first emitted object term is taken. Lookup suffixes (`__icontains`, `__gt`) are out of scope per spec §7.

**Spec reference:** [docs/superpowers/specs/2026-05-22-rdfmodel-walking-skeleton-design.md](../specs/2026-05-22-rdfmodel-walking-skeleton-design.md) §7.

**Issue:** [#8 RDFManager and RDFQuerySet](https://github.com/judaicalink/djangordf/issues/8).

---

## File structure

| File | Responsibility | Action |
|---|---|---|
| `djangordf/manager.py` | `RDFManager` (CRUD), `RDFQuerySet` | extend |
| `djangordf/__init__.py` | re-export `RDFQuerySet` | extend |
| `tests/test_manager.py` | unit tests for new CRUD + queryset | extend |

---

## Tasks

### Task 1 — `RDFManager.create`

- [ ] `create(**kwargs) -> instance`: build `model_class(**kwargs)`, call `instance.save()`, return.

### Task 2 — `RDFManager.get`

- [ ] `get(iri) -> instance`:
      - Coerce `iri` to `URIRef`.
      - Issue `CONSTRUCT { <iri> ?p ?o } WHERE { GRAPH <g> { <iri> ?p ?o } }`.
      - Empty graph → `raise self.model_class.DoesNotExist(str(iri))`.
      - Otherwise instantiate `model_class(iri=iri)` and hydrate.
- [ ] `_hydrate(instance, graph, subject)`: for each property with non-`None` predicate, `setattr(instance, attr, prop.from_rdf(graph, subject))`.

### Task 3 — Filter argument coercion helper

- [ ] `_object_term(prop, value) -> rdflib term`:
      - If `value` is `URIRef`, `Literal`, or `BNode`: return it.
      - If `prop` is `ObjectProperty` and `value` is an `RDFModel` with `.iri`: return `URIRef(value.iri)`.
      - Else: call `prop.to_rdf(URIRef("urn:_djangordf:_filter:dummy"), value)`, take the first triple's object term, raise `ValueError` if no triples emitted.

### Task 4 — `RDFManager.all` and `RDFManager.filter`

- [ ] `all() -> RDFQuerySet(self, [])`.
- [ ] `filter(**kwargs) -> RDFQuerySet`:
      - For each `attr, value`: validate `attr in model_class._properties`; resolve predicate, term; append `(predicate, term)`.
      - Unknown attribute → `ValueError`.
      - Attribute with `predicate=None` → `ValueError("Property %r has no predicate")`.

### Task 5 — `RDFQuerySet`

- [ ] `__init__(manager, triple_patterns)`: stores both; lazy cache `None`.
- [ ] `_build_subject_sparql()`: `SELECT DISTINCT ?s WHERE { GRAPH <g> { ?s a <class_iri> . [<predicate> <object> .]* } }`.
- [ ] `_fetch()`: runs the SELECT, calls `manager.get(s)` for each row, caches.
- [ ] `__iter__`, `__len__`, `count()`, `first()`.

### Task 6 — Package re-export

- [ ] `djangordf/__init__.py`: add `RDFQuerySet` to imports + `__all__`.

### Task 7 — Tests

- [ ] `tests/test_manager.py` — extend (keep existing tests for mocked save/delete):
      - `test_create_persists_and_returns_instance` — backend has the triples after create.
      - `test_get_roundtrips_iri_and_properties` — create then get, all property values match.
      - `test_get_raises_doesnotexist_for_missing_iri`.
      - `test_save_is_idempotent` — call twice, triple count unchanged.
      - `test_save_overwrites_stale_triples` — change a value, stale triple gone.
      - `test_delete_removes_all_triples_for_iri`.
      - `test_all_returns_queryset_with_every_instance`.
      - `test_filter_by_exact_value_returns_subset`.
      - `test_filter_unknown_attribute_raises`.
      - `test_queryset_len_and_count_match`.
      - `test_queryset_first_returns_none_when_empty`.
      - `test_queryset_is_lazy` — backend not hit at construction time (mock the manager.backend).

### Task 8 — Lint, test, push

- [ ] `flake8 djangordf tests setup.py` — clean.
- [ ] `pytest -q` — 100% pass; expect ~10–12 new tests, total >= 132.
- [ ] Commit per repo convention (English commits, no Claude attribution).
- [ ] Push branch, open PR against `development`, link issue #8.

---

## Done when

- `flake8` clean.
- All previous tests still green; new tests added.
- `create` → `get(iri)` roundtrip works for every property type.
- `save` is idempotent; updates overwrite stale triples.
- `delete` removes every `<iri> ?p ?o` triple.
- `get` raises `DoesNotExist` for missing IRIs.
- `all()` and `filter()` return a lazy `RDFQuerySet`; iteration / `len` / `count` / `first` work.
- PR merged; issue #8 closed; tracking issue #11 checkbox ticked.
