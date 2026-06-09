# QuerySet Ordering and Slicing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add ordering and slicing to `RDFQuerySet` so callers can write `Term.objects.all().order_by("title")[:10]` and have the manager generate the corresponding SPARQL with `ORDER BY`, `LIMIT`, and `OFFSET`. Closes GitHub issue #50.

**Architecture:** `RDFQuerySet` gains three new immutable fields — `_order_by` (tuple of `(attr, descending)` pairs), `_limit`, `_offset` — populated through new `order_by(*fields)` and `__getitem__(slice)` methods that each return a new `RDFQuerySet` carrying the updated state. The SPARQL builder grows two stages: (1) for each `order_by` field, mint a fresh `?ord_N` variable, append a `?s <predicate> ?ord_N .` triple inside the WHERE block, and project `?ord_N` into the SELECT clause; (2) emit `ORDER BY` / `LIMIT` / `OFFSET` clauses at the tail of the SPARQL string. Materialisation switches to keep-first-seen deduplication by subject IRI so that multi-valued ordered fields don't multiply rows. `__getitem__(int)` is the only path that forces materialisation; slices remain lazy.

**Tech stack:** Python 3.10+, rdflib 7.x, Django 3.2+, pytest 9.x, pytest-django 4.x.

**Spec reference:** [docs/superpowers/specs/2026-05-22-rdfmodel-walking-skeleton-design.md](../specs/2026-05-22-rdfmodel-walking-skeleton-design.md) §10 ("Cross-class queries, joins, ordering, slicing, advanced lookups"). The first half landed in #40/#43/#46/#48; this PR delivers ordering and slicing.

**Issue:** [#50 Slicing, order_by, and limit on RDFQuerySet](https://github.com/judaicalink/djangordf/issues/50).

---

## File structure

| Path | Responsibility | Action |
|---|---|---|
| `djangordf/manager.py` | `RDFQuerySet` ordering / slicing fields + SPARQL builder updates | extend |
| `tests/test_manager.py` | new ordering / slicing tests | extend |
| `docs/quickstart.md` | "Ordering and slicing" subsection after Q composition | extend |
| `docs/superpowers/plans/2026-06-09-queryset-ordering-slicing.md` | this plan | new |

---

## Tasks

### Task 1 — `RDFQuerySet` state

- [ ] Constructor: `__init__(manager, q=None, order_by=(), limit=None, offset=None)`. Tuples / ints are stored as-is; defaults preserve current behaviour.
- [ ] `_clone(**overrides)` private helper that copies all fields and applies overrides. All chainable methods go through it.

### Task 2 — `order_by(*fields)`

- [ ] Each field is a property name with optional leading `-` for descending. Validation deferred to materialisation (matches Django's lazy semantics).
- [ ] Returns a new queryset.
- [ ] `order_by()` with no fields clears any existing ordering.

### Task 3 — `__getitem__`

- [ ] `int` key: materialise, return `items[key]`, raise `IndexError` if out of range. Negative keys raise `IndexError("RDFQuerySet does not support negative indices")`.
- [ ] `slice` key: reject `step != None` with `TypeError`. Reject negative `start`/`stop` with `IndexError`. Otherwise return a new queryset with `_offset = start or self._offset or 0 + start` and `_limit = stop - start` (handling existing offsets/limits carefully — chained slices compose).
- [ ] Other types: `TypeError`.

### Task 4 — Slice composition rules

- [ ] If the queryset already has a `_limit`/`_offset` and you slice it again, compose:
      - new_offset = old_offset + new_start
      - new_limit = min(remaining_old_limit, new_stop - new_start)
- [ ] Document this in the docstring with a worked example.

### Task 5 — SPARQL builder updates

- [ ] In `_build_subject_sparql`:
      - Allocate `?ord_<N>` variables (counter shared with the Q walker's counter to avoid collisions).
      - For each ordered field: resolve the attribute on `model_class`, append `?s <predicate> ?ord_N .` to the body, project `?ord_N` into the SELECT list, and append the ordering token to a `ORDER BY` clause.
      - SELECT clause becomes `SELECT DISTINCT ?s ?ord_1 ?ord_2 ...` so the projection drives DISTINCT correctly.
      - Append `ORDER BY <tokens>` / `LIMIT N` / `OFFSET M` outside the GRAPH block.
      - When no ordering and no slicing is configured, the emitted SPARQL is byte-equivalent to today.

### Task 6 — `_fetch` deduplication

- [ ] Iterate query rows; keep first occurrence per subject IRI (`dict.fromkeys` style).
- [ ] Then call `manager.get(s)` for each unique subject, in order.

### Task 7 — `first()` updates

- [ ] Reimplement `first()` as `next(iter(self._clone(limit=1)), None)` to leverage the new slicing path.

### Task 8 — Tests

Extend `tests/test_manager.py`:

- [ ] `test_slice_returns_first_n_items`.
- [ ] `test_slice_with_offset_returns_window`.
- [ ] `test_index_returns_single_item`.
- [ ] `test_index_out_of_range_raises_index_error`.
- [ ] `test_negative_index_raises`.
- [ ] `test_negative_slice_start_or_stop_raises`.
- [ ] `test_slice_step_raises`.
- [ ] `test_order_by_ascending`.
- [ ] `test_order_by_descending`.
- [ ] `test_order_by_multiple_fields`.
- [ ] `test_order_by_clears_when_called_with_no_args`.
- [ ] `test_order_by_unknown_attribute_raises_on_iteration`.
- [ ] `test_slice_composes_with_prior_slice` (chained `qs[10:20][2:4]`).
- [ ] `test_order_by_chains_with_filter_and_slice`.

### Task 9 — Docs

- [ ] `docs/quickstart.md`: "Ordering and slicing" subsection.

### Task 10 — Lint, test, push

- [ ] `flake8 djangordf tests setup.py examples docs/conf.py` clean.
- [ ] `pytest -q` — green; expect ~14 new tests, total ≈ 248.
- [ ] `sphinx-build -W -b html docs docs/_build/html` exits 0.
- [ ] Logical commits per repo convention.
- [ ] Push branch, open PR against `development` linking issue #50.

---

## Done when

- All acceptance bullets on #50 pass.
- Existing 234 tests stay green; new tests added.
- Sphinx strict build green.
- PR merged; issue #50 closed.
