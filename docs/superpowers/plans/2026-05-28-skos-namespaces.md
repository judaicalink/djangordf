# SKOS Defaults and NamespaceRegistry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the full `NamespaceRegistry` and the SKOS-as-default-meta-layer convenience. After this, a SKOS thesaurus class needs no `predicate=` arguments on `pref_label`, `alt_label`, `broader`, … and no `Meta.class_iri`. Closes GitHub issue #9.

**Architecture:** `NamespaceRegistry` is a per-process registry seeded with the common prefixes (rdf, rdfs, owl, xsd, skos, dct, foaf). `register(prefix, uri)` extends it, `bind_to_graph(graph)` makes Turtle output pretty, `resolve(curie_or_iri)` turns `"skos:Concept"` into a `URIRef`. A module-level singleton `registry` lives in `djangordf/namespaces.py`. `DjangordfConfig.ready()` reads `settings.DJANGORDF_NAMESPACES` and feeds it into the registry — the same work is exposed as `apply_namespace_settings()` so tests can drive it without restarting Django. `skos.py` now delegates its `resolve_curie` to the registry and adds `DEFAULT_PREDICATES`, the convention map (`pref_label` → `skos:prefLabel`, …) that the metaclass consults whenever a `Property` has `predicate=None`.

**Spec deviation (intentional):** Spec §6 specifies that the metaclass `raise ImproperlyConfigured` when a `Property` has no `predicate=` and no SKOS convention match. This plan instead **silently leaves the predicate as `None`** so that existing `Property()` test stubs and future extension-point experiments keep working; `_to_triples` already skips properties whose predicate is `None`. Issue #9 acceptance does not require raising. Revisit if the silent path produces surprises in real models.

**Tech Stack:** Python 3.10+, rdflib 7.x, Django 3.2+, pytest 9.x, pytest-django 4.x.

**Spec reference:** [docs/superpowers/specs/2026-05-22-rdfmodel-walking-skeleton-design.md](../specs/2026-05-22-rdfmodel-walking-skeleton-design.md) §8 (with metaclass touch from §6).

**Issue:** [#9 SKOS defaults and NamespaceRegistry](https://github.com/judaicalink/djangordf/issues/9).

---

## File structure

| File | Responsibility | Action |
|---|---|---|
| `djangordf/namespaces.py` | `LangString`, `NamespaceRegistry`, `registry` singleton, `apply_namespace_settings` | extend (keep `LangString`) |
| `djangordf/skos.py` | SKOS class IRI re-export, `resolve_curie` via registry, `DEFAULT_PREDICATES` map | extend |
| `djangordf/apps.py` | `DjangordfConfig.ready()` reads `DJANGORDF_NAMESPACES` | extend |
| `djangordf/models.py` | metaclass: implicit SKOS predicate assignment | tiny edit |
| `djangordf/__init__.py` | re-export `NamespaceRegistry`, `registry` | extend |
| `tests/test_namespaces.py` | registry unit tests | extend |
| `tests/test_skos.py` | DEFAULT_PREDICATES contents | extend |
| `tests/test_models.py` | implicit SKOS predicate via metaclass | extend |

---

## Tasks

### Task 1 — `NamespaceRegistry` in `djangordf/namespaces.py`

- [ ] Add `NamespaceRegistry` class. `__init__` seeds the defaults dict:
      `rdf`, `rdfs`, `owl`, `xsd`, `skos`, `dct`, `foaf` (use rdflib's
      `Namespace`/`DefinedNamespace` objects so callers can interpolate).
- [ ] `register(prefix: str, uri: str | rdflib.Namespace) -> None`:
      store/overwrite. Wrap raw strings in `rdflib.Namespace`.
- [ ] `bind_to_graph(graph)`: iterate bindings and call `graph.bind(prefix, ns, override=True)`.
- [ ] `resolve(value)`:
      - `URIRef` passthrough.
      - `str` starting with `http://`, `https://`, `urn:` → `URIRef`.
      - `str` containing `:` → split prefix/local; unknown prefix raises `ValueError(f"Unknown CURIE prefix: {prefix!r}")`.
      - plain string with no colon → `URIRef(value)` passthrough.
- [ ] Module-level singleton: `registry = NamespaceRegistry()`.
- [ ] `apply_namespace_settings(extra: dict | None = None) -> None` helper:
      reads `getattr(settings, "DJANGORDF_NAMESPACES", {})` (or `extra` if
      supplied for tests), calls `registry.register` for each pair.
      Catches `ImproperlyConfigured` from a not-yet-configured Django so
      the helper is safe to call at import-time test fixtures.

### Task 2 — `djangordf/skos.py`

- [ ] Keep `Concept = SKOS.Concept`.
- [ ] Drop the local `_CURIE_TABLE` and rewrite `resolve_curie` as a thin
      wrapper that calls `registry.resolve(value)`. Keep raising
      `TypeError` for non-`str`/`URIRef` inputs.
- [ ] Add `DEFAULT_PREDICATES: dict[str, URIRef]` containing exactly:
      `pref_label`, `alt_label`, `hidden_label`, `definition`, `note`,
      `broader`, `narrower`, `related`, `exact_match`, `close_match`,
      `in_scheme` → their SKOS predicates.

### Task 3 — `djangordf/apps.py`

- [ ] Add `ready(self)` to `DjangordfConfig` calling
      `apply_namespace_settings()` from `djangordf.namespaces`.

### Task 4 — Metaclass implicit predicate

- [ ] In `RDFModelMeta.__new__`, after `cls._properties` is populated,
      iterate properties: when `prop.predicate is None`, look up
      `attr_name` in `DEFAULT_PREDICATES`; if found assign
      `prop.predicate`. Leave `None` otherwise (silent).
- [ ] No new exception. `_to_triples` continues to skip predicate-less
      properties.

### Task 5 — `djangordf/__init__.py`

- [ ] Re-export `NamespaceRegistry` and `registry` (sorted alphabetically
      into `__all__`).

### Task 6 — Tests

- [ ] `tests/test_namespaces.py` — extend:
      - registry has the seven default prefixes resolvable.
      - `register` then `resolve` roundtrip for a new prefix.
      - `resolve` passes full IRIs through unchanged.
      - `resolve` raises `ValueError` on unknown prefix.
      - `bind_to_graph` binds all prefixes to a fresh `Graph`.
      - `apply_namespace_settings` with explicit `extra` dict registers entries.
- [ ] `tests/test_skos.py` — extend:
      - `DEFAULT_PREDICATES["pref_label"] == SKOS.prefLabel`.
      - `DEFAULT_PREDICATES["broader"] == SKOS.broader`.
      - Map has the eleven expected keys.
- [ ] `tests/test_models.py` — extend:
      - Define an `RDFModel` with `pref_label = LangStringProperty()` (no
        `predicate=`); assert `cls._properties["pref_label"].predicate == SKOS.prefLabel`.
      - Define one with `broader = ObjectProperty("self")`; assert it
        resolves to `SKOS.broader`.

### Task 7 — Lint, test, push

- [ ] `flake8 djangordf tests setup.py` — clean.
- [ ] `pytest -q` — 100% pass.
- [ ] Commit per repo convention (English commit messages, no Claude attribution).
- [ ] Push branch, open PR against `development`, link issue #9.

---

## Done when

- `flake8` clean.
- All previous tests still green; six+ new tests added; total >= 109.
- `registry.resolve("skos:Concept") == SKOS.Concept`.
- `DJANGORDF_NAMESPACES` setting is honoured via the app's `ready()`.
- A property named `pref_label` on an `RDFModel` subclass without
  explicit `predicate=` resolves to `skos:prefLabel` through the
  metaclass.
- A class without `Meta.class_iri` still defaults to `skos:Concept` (no
  regression).
- PR merged; issue #9 closed; tracking issue #11 checkbox ticked.
