# Walking-Skeleton Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lock down the MVP walking skeleton with the twelve spec-named unit tests (spec §9) and ship the executable acceptance script (`examples/walking_skeleton.py`). After this, the design spec's acceptance criteria are met: the script in §9 runs green against the in-memory backend without touching djangordf. Closes GitHub issue #10.

**Architecture:** Two new test files (`tests/test_rdfmodel.py`, `tests/test_walking_skeleton.py`), one new example script (`examples/walking_skeleton.py`), and one settings polish. A behaviour change in `ObjectProperty.from_rdf` is required: the spec script reads `reloaded.broader[0].iri`, so the property must materialise its targets as **lightweight target-class instances with only `iri` populated** (not bare `URIRef` strings as today). No recursive hydration — followers of the link still call `target_class.objects.get(iri)` if they want full data. This avoids cycle hazards and N+1 explosions while satisfying the spec.

**Spec reference:** [docs/superpowers/specs/2026-05-22-rdfmodel-walking-skeleton-design.md](../specs/2026-05-22-rdfmodel-walking-skeleton-design.md) §9, §11.

**Issue:** [#10 RDFModel test suite and acceptance script](https://github.com/judaicalink/djangordf/issues/10).

---

## File structure

| File | Responsibility | Action |
|---|---|---|
| `djangordf/properties.py` | `ObjectProperty.from_rdf` returns target-class instances | tiny edit |
| `tests/test_properties.py` | update the `from_rdf returns iris` test | tiny edit |
| `tests/settings.py` | add namespace + graph defaults | extend |
| `tests/conftest.py` | optional `in_memory_backend` fixture | extend |
| `tests/test_rdfmodel.py` | twelve spec-named unit tests | new |
| `examples/walking_skeleton.py` | executable acceptance script | new |
| `tests/test_walking_skeleton.py` | runs the example script and asserts it exits 0 | new |

---

## Tasks

### Task 1 — ObjectProperty.from_rdf returns target-class instances

- [ ] Replace `URIRef(o)` with `target_class(iri=URIRef(o))` in both scalar and `many` branches. Construction sets `self.iri` and defaults for every other declared property — exactly the ghost-instance shape the spec assertion needs.

### Task 2 — Update the property-level read test

- [ ] `tests/test_properties.py::test_object_property_from_rdf_returns_iris`: rename helper variables and assert `result.iri == URIRef(...)` on a returned instance. Adjust the docstring: hydration of the target instance fields is still the manager's job — `from_rdf` only sets `.iri`.

### Task 3 — `tests/settings.py` defaults

- [ ] Add `DJANGORDF_DEFAULT_NAMESPACE = "http://example.org/d/"` and `DJANGORDF_DEFAULT_GRAPH = "http://example.org/g"` next to the existing `DJANGORDF_BACKEND` line.

### Task 4 — `tests/conftest.py` fixture

- [ ] Keep the existing `load_graph` helper.
- [ ] Add `in_memory_backend` opt-in fixture: configures the settings (no-op if already set), serves as documentation that a test wants isolation. Tests already get a fresh backend per RDFModel-subclass-per-test because the metaclass spins up a new manager — this fixture is mostly a hook for any future autouse policy.

### Task 5 — `tests/test_rdfmodel.py`: twelve named spec tests

The exact names from spec §9 — each test is small and uses an isolated `Term` class declared inside the test (unique class name avoids registry overwrites).

- [ ] `test_create_mints_iri` — `Term.objects.create()` produces an IRI starting with the configured namespace.
- [ ] `test_save_writes_rdf_type_triple` — `(<iri>, rdf:type, <class_iri>)` is in the store after `save()`.
- [ ] `test_save_writes_all_properties` — every declared property lands as a triple with the expected predicate.
- [ ] `test_skos_default_predicate_for_pref_label` — a `pref_label = LangStringProperty()` without `predicate=` resolves to `skos:prefLabel` via the metaclass.
- [ ] `test_curie_class_iri_resolves` — `Meta.class_iri = "foaf:Person"` resolves to `FOAF.Person`.
- [ ] `test_get_round_trip` — `create` → `get(iri)` roundtrips every property value.
- [ ] `test_save_is_idempotent` — calling `save()` twice leaves the triple count unchanged.
- [ ] `test_update_overwrites_stale_triples` — change a value and call `save()`; the previous value is gone.
- [ ] `test_delete_removes_all_triples` — `delete()` removes every `<iri> ?p ?o` triple.
- [ ] `test_lang_string_round_trip` — `LangString("Buch", "de")` survives create + get.
- [ ] `test_object_property_self_reference` — a `broader` link roundtrips and the resolved instance carries the correct `.iri`.
- [ ] `test_get_missing_iri_raises_does_not_exist` — `get(iri="...not-here...")` raises `Term.DoesNotExist`.

### Task 6 — Walking-skeleton example script

- [ ] `examples/walking_skeleton.py`:
      - `#!/usr/bin/env python` shebang.
      - Configures Django (`django.setup()` after `os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")`).
      - Mirrors spec §9 verbatim: declares `Term`, `create` two instances, `get` the second, asserts `.broader[0].iri == buch.iri` and the language-tag-present check.
      - Exits 0 on success.

### Task 7 — Walking-skeleton acceptance test

- [ ] `tests/test_walking_skeleton.py`:
      - Run the example via `subprocess.run([sys.executable, "examples/walking_skeleton.py"])`.
      - Assert returncode 0 and no stderr noise (or capture and report it).

### Task 8 — Lint, full test run, push

- [ ] `flake8 djangordf tests setup.py examples` — clean.
- [ ] `pytest -q` — green; expect ~13 new tests, total ≈ 151.
- [ ] Commit per repo convention (English commits, no Claude attribution).
- [ ] Push branch, open PR against `development`, link issue #10.

---

## Done when

- `flake8` clean.
- All previous tests still green; the twelve named tests pass; the walking-skeleton example runs green.
- `examples/walking_skeleton.py` matches spec §9 and exits 0.
- PR merged; issue #10 closed; tracking issue #11 fully ticked.
