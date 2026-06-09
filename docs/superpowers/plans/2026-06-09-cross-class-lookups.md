# Cross-Class Lookups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let callers write `Term.objects.filter(broader__pref_label="Buch")` and have `RDFManager` generate the corresponding join-style SPARQL pattern. Brings the biggest remaining UX win for actual knowledge-graph queries; complements the existing single-segment `filter()` rather than replacing it. Closes GitHub issue #40.

**Architecture:** `RDFManager.filter(**kwargs)` parses each key on `__` boundaries and walks the segments, asking each segment's `Property` for its predicate and (if non-terminal) its `target_class`. Each hop contributes one triple to the queryset's pattern list. The pattern list itself moves from the current `[(predicate, object_term)]` shape to `[(subject_var_or_iri, predicate, object_term_or_var)]` 3-tuples so intermediate variables can be threaded across hops. `RDFQuerySet._build_subject_sparql` is rewritten to render those 3-tuples (using `.n3()` for rdflib terms and emitting `?var` strings verbatim for variables). Lookup suffixes (`__exact`, `__icontains`, etc.) stay out of scope and become a future ticket. Single-segment filters keep working because they collapse to a one-pattern list with `?s` as the subject.

**Tech stack:** Python 3.10+, rdflib 7.x, Django 3.2+, pytest 9.x, pytest-django 4.x.

**Spec reference:** [docs/superpowers/specs/2026-05-22-rdfmodel-walking-skeleton-design.md](../specs/2026-05-22-rdfmodel-walking-skeleton-design.md) §10 ("Cross-class queries, joins, ordering, slicing, advanced lookups"). This plan covers the join half only.

**Issue:** [#40 Cross-class lookups in RDFManager.filter](https://github.com/judaicalink/djangordf/issues/40).

---

## File structure

| Path | Responsibility | Action |
|---|---|---|
| `djangordf/manager.py` | parse `__` paths, walk segments, emit 3-tuples | extend |
| `djangordf/manager.py` | `RDFQuerySet._build_subject_sparql` consumes 3-tuples | extend |
| `tests/test_manager.py` | new cross-class lookup tests | extend |
| `docs/quickstart.md` | show the new pattern after the existing filter example | extend |
| `docs/superpowers/plans/2026-06-09-cross-class-lookups.md` | this plan | new |

---

## Tasks

### Task 1 — Shape the pattern list as 3-tuples

- [ ] `RDFQuerySet.__init__` keeps the existing signature but now stores 3-tuples internally. Convert any existing call sites that still pass 2-tuples at the boundary (only `RDFManager.filter` and `RDFManager.all` produce them).
- [ ] `RDFQuerySet._build_subject_sparql` renders each entry as `<s_repr> <p_repr> <o_repr> .`, where the repr is `.n3()` for rdflib terms and a verbatim `?var` string for variables (`subject.startswith("?")` or `obj` instance check).

### Task 2 — Path walker in `RDFManager.filter`

- [ ] Replace the body of `filter` with a loop over `kwargs.items()`:
      - Split the key on `__`.
      - Walk segments left-to-right with `current_var = "?s"` and `current_cls = self.model_class`.
      - For each segment:
        - `prop = current_cls._properties.get(seg)`; on miss raise `ValueError("Unknown attribute ...")`.
        - `prop.predicate is None` → `ValueError("Property ... has no predicate; cannot use it in filter()")`.
        - If this is the last segment, emit `(current_var, prop.predicate, self._object_term(prop, value))`.
        - Otherwise: if `prop` is not an `ObjectProperty`, raise `ValueError("non-terminal lookup segment ... is not an ObjectProperty; cannot span")`. Mint a new variable `?v<N>` (N counts intermediates across the entire kwargs dict so they don't collide), emit `(current_var, prop.predicate, next_var)`, and advance `current_var = next_var`, `current_cls = prop.target_class`.

### Task 3 — Variable minting

- [ ] A single counter scoped to the `filter` call so multiple kwargs can share the same `?v1`/`?v2`/... namespace without collision. Reset per `filter()` invocation, not per queryset.

### Task 4 — `RDFManager.all` and `RDFManager.filter` returns

- [ ] `RDFManager.all()` returns `RDFQuerySet(self, [])` — unchanged.
- [ ] `RDFManager.filter(**kwargs)` returns `RDFQuerySet(self, triple_patterns)` with the new 3-tuple shape.

### Task 5 — Tests

Extend `tests/test_manager.py`:

- [ ] `test_filter_spans_one_objectproperty` — `Term.objects.filter(broader__title=...)` returns the expected child instances.
- [ ] `test_filter_spans_two_objectproperty_hops` — `Term.objects.filter(broader__broader__title=...)` traverses two hops.
- [ ] `test_filter_spans_into_langstring_property` — terminal LangString comparison works with both a plain string and a `LangString(value, lang)`.
- [ ] `test_filter_combines_simple_and_spanning_kwargs` — both kwargs constrain together.
- [ ] `test_filter_unknown_segment_on_path_raises`.
- [ ] `test_filter_nonterminal_segment_must_be_objectproperty` — passing a DataProperty as a non-terminal raises.
- [ ] `test_filter_path_with_predicate_none_raises`.
- [ ] `test_filter_simple_single_segment_still_works` — regression for the existing path.

### Task 6 — Docs

- [ ] `docs/quickstart.md`: add a short section after the existing "Query lazily" block showing `Term.objects.filter(broader__pref_label="Buch")` and a chained two-hop example. Note that lookup suffixes (`__icontains`, `__gt`, ...) are out of scope for this release.

### Task 7 — Lint, test, push

- [ ] `flake8 djangordf tests setup.py examples docs/conf.py` clean.
- [ ] `pytest -q` — green; expect ~8 new tests, total ≈ 198.
- [ ] `sphinx-build -W -b html docs docs/_build/html` exits 0.
- [ ] Logical commits per the repo convention (English commit messages, no AI attribution).
- [ ] Push branch, open PR against `development` linking issue #40.

---

## Done when

- All acceptance bullets on #40 pass.
- Existing 190 tests stay green; new tests added.
- Sphinx strict build green.
- PR merged; issue #40 closed.
