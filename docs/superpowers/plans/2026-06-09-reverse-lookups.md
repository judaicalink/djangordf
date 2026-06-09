# Reverse Lookups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `reverse=True` to `ObjectProperty` so the manager can navigate a relationship from the target side without declaring both directions explicitly. The new property is read-only — it emits no triples on save, hydrates by reading the predicate "from the other end", and swaps the subject/object position in filter triples. Closes GitHub issue #46.

**Architecture:** `ObjectProperty(reverse=True)` flips the direction the property thinks about. `to_rdf` returns `[]`; `from_rdf` does `graph.subjects(predicate, subject)` and wraps the matches as ghost target-class instances; `RDFManager.filter`'s path walker emits `(<next_var>, predicate, current_var)` instead of `(current_var, predicate, <next_var>)`. `RDFManager.get` issues an extra reverse-direction CONSTRUCT (`?s ?p <iri>`) only when the model declares at least one reverse property and merges its result into the forward graph before hydration, so models without reverse properties pay no additional round-trip cost. `reverse=True` is mutually exclusive with `inverse=<name>`: the former is read-only, the latter implies mirror writes, and the combination would be incoherent. The `predicate` is required on a `reverse=True` declaration — the metaclass's SKOS-convention map is not applied (a "virtual" property should not silently inherit forward semantics).

**Tech stack:** Python 3.10+, rdflib 7.x, Django 3.2+, pytest 9.x, pytest-django 4.x.

**Spec reference:** [docs/superpowers/specs/2026-05-22-rdfmodel-walking-skeleton-design.md](../specs/2026-05-22-rdfmodel-walking-skeleton-design.md) §10. Out-of-scope notes in PR #41 and PR #44 both flagged reverse-relation navigation as a future ticket.

**Issue:** [#46 Reverse-lookups via ObjectProperty(reverse=True)](https://github.com/judaicalink/djangordf/issues/46).

---

## File structure

| Path | Responsibility | Action |
|---|---|---|
| `djangordf/properties.py` | `ObjectProperty(reverse=...)` + swapped `to_rdf` / `from_rdf` | extend |
| `djangordf/models.py` | metaclass skips SKOS-default for reverse properties | tiny edit |
| `djangordf/manager.py` | filter path-walker swap + get's optional reverse CONSTRUCT | extend |
| `tests/test_properties.py` | reverse property unit tests | extend |
| `tests/test_reverse_lookups.py` | end-to-end behaviour against `InMemoryBackend` | new |
| `docs/quickstart.md` | "Reverse-relation navigation" subsection after lookup suffixes | extend |
| `docs/superpowers/plans/2026-06-09-reverse-lookups.md` | this plan | new |

---

## Tasks

### Task 1 — `ObjectProperty` constructor + flag

- [ ] Add `reverse: bool = False` to `__init__`.
- [ ] If `reverse and inverse is not None` → `ValueError("ObjectProperty cannot combine reverse=True with inverse=...; reverse is read-only")`.
- [ ] Store the flag as `self.reverse`.

### Task 2 — Read/write behaviour

- [ ] `to_rdf(subject, value)`: when `self.reverse` is true, return `[]` regardless of `value`.
- [ ] `from_rdf(graph, subject)`:
      - `objects = list(graph.subjects(self.predicate, subject))` when `self.reverse`.
      - Wrap each match as `target_cls(iri=URIRef(s))` exactly like the forward path.
      - Keep the `many=True/False` behaviour identical to forward.

### Task 3 — Metaclass: do not apply SKOS default

- [ ] In `RDFModelMeta.__new__`, when assigning `DEFAULT_PREDICATES[attr]` to `prop.predicate is None`, skip if `getattr(prop, "reverse", False)` is true.

### Task 4 — `RDFManager.filter` path walker swap

- [ ] When walking segments, detect `getattr(prop, "reverse", False)` per segment.
- [ ] Non-terminal hop:
      - Forward: `(current_var, prop.predicate, next_var)`.
      - Reverse: `(next_var, prop.predicate, current_var)`.
      - Either way, mint `next_var` and advance `current_var = next_var`, `current_cls = prop.target_class`.
- [ ] Terminal segment:
      - Forward exact: `(current_var, prop.predicate, _object_term(prop, value))`.
      - Reverse exact: `(_object_term(prop, value), prop.predicate, current_var)`.
      - Forward suffix: `(current_var, prop.predicate, terminal_var)` + FILTER.
      - Reverse suffix: `(terminal_var, prop.predicate, current_var)` + FILTER on `terminal_var`.

### Task 5 — `RDFManager.get` optional reverse CONSTRUCT

- [ ] Helper `_has_reverse_properties()` returns true if any declared property has `reverse=True`.
- [ ] In `get(iri)`:
      - Always issue the forward CONSTRUCT first; raise `DoesNotExist` on empty graph.
      - If `_has_reverse_properties()` is true, issue a second CONSTRUCT — `CONSTRUCT { ?s ?p <iri> } WHERE { GRAPH <g> { ?s ?p <iri> } }` — and merge it into the forward graph before `_hydrate`.

### Task 6 — Tests

`tests/test_properties.py`:

- [ ] `test_object_property_reverse_keyword_stored`.
- [ ] `test_object_property_reverse_default_false`.
- [ ] `test_object_property_reverse_with_inverse_raises`.
- [ ] `test_object_property_reverse_to_rdf_returns_empty`.
- [ ] `test_object_property_reverse_from_rdf_reads_inverse_direction`.

`tests/test_reverse_lookups.py` (new):

- [ ] `test_save_does_not_emit_triples_for_reverse_property`.
- [ ] `test_get_hydrates_reverse_property_with_target_ghost_instances`.
- [ ] `test_filter_terminal_reverse_segment_emits_swapped_pattern`.
- [ ] `test_filter_non_terminal_reverse_then_forward`.
- [ ] `test_filter_reverse_segment_with_suffix_emits_swapped_pattern_and_filter`.

Metaclass test in `tests/test_models.py`:

- [ ] `test_reverse_property_does_not_inherit_skos_default_predicate`.

### Task 7 — Docs

- [ ] `docs/quickstart.md` gains a "Reverse-relation navigation" subsection: `Author` / `Book` example with `reverse=True`, a `filter(books__title=...)` query, and an `author.books` attribute read.

### Task 8 — Lint, test, push

- [ ] `flake8 djangordf tests setup.py examples docs/conf.py` clean.
- [ ] `pytest -q` — green; expect ~11 new tests, total ≈ 220.
- [ ] `sphinx-build -W -b html docs docs/_build/html` exits 0.
- [ ] Logical commits per repo convention.
- [ ] Push branch, open PR against `development` linking issue #46.

---

## Done when

- All acceptance bullets on #46 pass.
- Existing 209 tests stay green; new tests added.
- Sphinx strict build green.
- PR merged; issue #46 closed.
