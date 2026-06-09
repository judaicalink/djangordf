# Lookup Suffixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `RDFManager.filter` with Django-style lookup suffixes so callers can write `Term.objects.filter(title__icontains="buch")`, `Term.objects.filter(count__gt=5)`, `Term.objects.filter(title__in=["a", "b"])` and any other suffix listed in #43. Each suffix becomes a SPARQL `FILTER(...)` clause attached to a triple that binds the relevant property value to a fresh variable. Closes GitHub issue #43.

**Architecture:** `RDFManager.filter` already walks `__`-separated paths and emits triple patterns. This change adds a small **suffix-peeling** step before path walking: if the last segment matches a known suffix and the key has ≥ 2 segments, we strip it off and remember it. After the path walker reaches the terminal segment, it dispatches on the suffix: `__exact` (and the absent-suffix case) keeps the current "bound triple" behaviour; every other suffix mints a fresh variable, emits `?s <pred> ?vN`, and appends a SPARQL FILTER expression to a new `RDFQuerySet` filter-clause list. `RDFQuerySet._build_subject_sparql` renders the filters after the triple patterns inside the same `GRAPH { ... }` block. Suffix detection is conservative: single-segment keys never steal a suffix, so `filter(exact=...)` still treats `exact` as a property name. The cross-class span feature composes with suffixes — the terminal handling runs after the path walker, on whichever class the path landed on.

**Tech stack:** Python 3.10+, rdflib 7.x, Django 3.2+, pytest 9.x, pytest-django 4.x.

**Spec reference:** [docs/superpowers/specs/2026-05-22-rdfmodel-walking-skeleton-design.md](../specs/2026-05-22-rdfmodel-walking-skeleton-design.md) §10 ("Cross-class queries, joins, ordering, slicing, advanced lookups") — second half.

**Issue:** [#43 Lookup suffixes in RDFManager.filter](https://github.com/judaicalink/djangordf/issues/43).

---

## File structure

| Path | Responsibility | Action |
|---|---|---|
| `djangordf/manager.py` | suffix peeling + FILTER generation + queryset filter list | extend |
| `tests/test_manager.py` | new per-suffix tests + composition with spans | extend |
| `docs/quickstart.md` | "Lookup suffixes" subsection after the cross-class lookup block | extend |
| `docs/superpowers/plans/2026-06-09-lookup-suffixes.md` | this plan | new |

---

## Tasks

### Task 1 — `RDFQuerySet` learns about FILTER clauses

- [ ] `RDFQuerySet.__init__(manager, triple_patterns, filter_clauses=())`. Store `filter_clauses` as a list of raw SPARQL expressions (strings without the leading `FILTER(...)` wrapper — the renderer wraps them).
- [ ] `_build_subject_sparql` appends one `FILTER(<expr>) .` per entry after the triple patterns.

### Task 2 — Suffix peeling in `RDFManager.filter`

- [ ] `_KNOWN_SUFFIXES` frozenset: `exact`, `iexact`, `contains`, `icontains`, `startswith`, `istartswith`, `endswith`, `iendswith`, `in`, `gt`, `gte`, `lt`, `lte`.
- [ ] `_peel_suffix(segments)` returns `(path_segments, suffix)`. If `len(segments) >= 2` and `segments[-1] in _KNOWN_SUFFIXES`, peel; otherwise return `(segments, "exact")`.

### Task 3 — Terminal segment handling per suffix

- [ ] After the path walker reaches the terminal `(current_var, prop)`:
      - If suffix is `exact`: emit bound triple as today.
      - Else: mint a fresh `?vN` (continue the variable counter shared with intermediate vars), emit `(current_var, prop.predicate, next_var)`, then build the SPARQL FILTER expression and append it to `filter_clauses`.
- [ ] FILTER builders (one helper per suffix family):
      - `iexact`, `contains`/`icontains`, `startswith`/`istartswith`, `endswith`/`iendswith` use `STR()` and (for the `i` variants) `LCASE()` on both sides.
      - `in`: rebuild each list element through `_object_term(prop, item)` and join with `, ` inside `IN (...)`. Reject non-iterables with a clear `TypeError`.
      - `gt`, `gte`, `lt`, `lte`: serialise the value through `_object_term(prop, value)` so typed literals (`"5"^^xsd:integer`) come out correctly.

### Task 4 — `RDFManager.filter` integration

- [ ] Track `filter_clauses` next to `triple_patterns` inside `filter()`.
- [ ] Pass both to the queryset constructor.

### Task 5 — Tests

Extend `tests/test_manager.py`:

- [ ] `test_filter_iexact_matches_case_insensitively`
- [ ] `test_filter_contains_substring`
- [ ] `test_filter_icontains_substring_case_insensitive`
- [ ] `test_filter_startswith` / `test_filter_istartswith`
- [ ] `test_filter_endswith` / `test_filter_iendswith`
- [ ] `test_filter_in_membership` (string list and integer list)
- [ ] `test_filter_gt_gte_lt_lte` (typed-literal comparisons against `XSD.integer`)
- [ ] `test_filter_suffix_composes_with_cross_class_span` — `broader__title__icontains="par"`
- [ ] `test_filter_single_segment_exact_still_works` — regression
- [ ] `test_filter_property_named_like_a_suffix_not_peeled` — `filter(exact="x")` still treats `exact` as the attribute name (test by declaring a property called `exact` on a model).

### Task 6 — Docs

- [ ] `docs/quickstart.md`: extend with a "Lookup suffixes" subsection right after the "Cross-class lookups" section. Cover `__icontains`, `__in`, and `__gt` with one example each, and mention that the suffix attaches to the terminal segment after any `__`-spanning.

### Task 7 — Lint, test, push

- [ ] `flake8 djangordf tests setup.py examples docs/conf.py` clean.
- [ ] `pytest -q` — green; expect ~12 new tests, total ≈ 210.
- [ ] `sphinx-build -W -b html docs docs/_build/html` exits 0.
- [ ] Logical commits per the repo convention.
- [ ] Push branch, open PR against `development` linking issue #43.

---

## Done when

- Every suffix on #43's table produces the expected subset against `InMemoryBackend`.
- Cross-class spans compose with suffixes.
- Existing 198 tests stay green; new tests added.
- Sphinx strict build green.
- PR merged; issue #43 closed.
