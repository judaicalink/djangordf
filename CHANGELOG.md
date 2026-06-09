# Changelog

All notable changes to djangordf will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-06-09

Inverse properties on `ObjectProperty`. Declaring
`broader = ObjectProperty("self", inverse="narrower")` now keeps both
directions of the relationship in the triple store and lets callers
read the back-pointer as a Python attribute.

### Added
- `ObjectProperty(..., inverse="<attr-name>")` keyword. The string
  names a property on the target class; lazy `inverse_property` and
  `inverse_predicate` accessors resolve it through the model registry
  on first access and raise `ValueError` only when needed.
- Mirror semantics in `RDFManager.save`: each save composes a
  multi-statement SPARQL update that strips stale mirror triples on
  any previous target (`WITH <graph> DELETE { ?s <inverse> <self> }`)
  and writes the new forward + mirror triples in one `INSERT DATA`
  block. Reassigning `child.broader` from one parent to another now
  keeps the matching `narrower` back-pointers in sync.
- Mirror strips in `RDFManager.delete`: every inverse predicate the
  model declares gets its own `DELETE { ?s <inverse> <self> }` pass,
  so deleting an instance removes the back-pointers from every
  referenced target.
- `generate_ontology()` emits `(predicate, owl:inverseOf, inverse_predicate)`
  once per declared pair (deduplicated lexicographically) so the
  serialised schema matches the runtime semantics.
- Quickstart docs show the new declaration and the back-read pattern.

### Notes
- `WITH <graph>` in SPARQL 1.1 Update scopes only the directly
  following Modify operation. The implementation now prefixes every
  `DELETE WHERE` with its own `WITH <graph>` so the inverse-DELETEs
  hit the configured graph; an earlier draft had silently routed
  them to the default graph.
- Inverse handling is implemented for `ObjectProperty` only.
  `URIProperty`/`DataProperty`/`LangStringProperty` deliberately stay
  out of scope (`inverse` makes sense for instance-to-instance links).

## [0.4.1] - 2026-06-09

Bug-fix release responding to production feedback from the Haskala
library integration. The 0.4.0 wheel on PyPI was unusable — see #29.

### Fixed
- **Packaging (#29).** `setup.py` now uses
  `find_packages(include=['djangordf', 'djangordf.*'])` so the wheel
  actually contains `djangordf.backends`, `djangordf.management`, and
  `djangordf.management.commands`. The 0.4.0 wheel shipped only the
  top-level package and every `import djangordf` raised
  `ModuleNotFoundError: No module named 'djangordf.backends'`.
- **Standalone imports (#30).** `RDFModelMeta` no longer runs
  `_build_meta` for the abstract `RDFModel` base, and `_build_meta`
  swallows `ImproperlyConfigured` from Django's lazy settings so
  `from djangordf.backends.fuseki import FusekiBackend` and friends
  succeed in non-Django scripts (or before `django.setup()` has run).
  User-defined subclasses still get a sensible `_meta` via the
  existing `urn:djangordf:...` fallbacks.

### Changed
- **`FusekiBackend.update` returns the HTTP response (#31).** The
  abstract `TripleStoreBackend.update` is now documented as
  potentially returning a value; `FusekiBackend` forwards the
  underlying `requests.Response` so callers can distinguish 200 vs.
  204 and inspect headers. `InMemoryBackend.update` still returns
  `None`.

### Added
- `tests/test_packaging.py` pins all three fixes via a regression
  test for `find_packages` and three subprocess tests that scrub
  `DJANGO_SETTINGS_MODULE` from the env before importing.
- `requirements-dev.txt` declares `setuptools>=68` so the new
  regression test runs on Python 3.12+ (where setuptools is no
  longer bundled with the stdlib).

## [0.4.0] - 2026-05-30

Ontology generation from declared `RDFModel` classes — delivering on
the project's "Modelle generieren Ontologie" tagline.

### Added
- `djangordf.ontology.generate_ontology(models=None, graph=None)`
  returns an `rdflib.Graph` describing the schema of the registered
  models: `owl:Class` declarations, `rdfs:label` + `rdfs:comment`
  annotations, `rdfs:subClassOf` for `RDFModel` inheritance,
  `owl:DatatypeProperty`/`owl:ObjectProperty` declarations for custom
  predicates (external SKOS/FOAF/etc. predicates are deliberately not
  re-declared), `rdfs:domain`/`rdfs:range`, and blank-node
  `owl:Restriction`s with `owl:minCardinality 1` for `required=True`
  and `owl:maxCardinality 1` for `many=False`.
- `python manage.py dump_ontology [--output PATH] [--format {turtle,xml,json-ld,n3}]`
  thin wrapper around the function.
- `djangordf.generate_ontology` re-export at the package root.
- Sphinx documentation page for `djangordf.ontology` and a Quickstart
  blurb showing the management command.

### Notes
- External predicate detection is based on the seeded namespace
  registry prefixes (`rdf`, `rdfs`, `owl`, `xsd`, `skos`, `dct`,
  `foaf`). Any predicate IRI starting with one of these namespaces is
  treated as already-declared by its source ontology and is therefore
  annotated only with per-class `rdfs:domain`/`rdfs:range`/cardinality
  statements.

## [0.3.1] - 2026-05-29

Documentation-only release. No API changes.

### Added
- Sphinx documentation site under `docs/` (MyST sources, Furo theme,
  autodoc reference for `djangordf.models`, `.properties`, `.manager`,
  `.namespaces`, `.skos`, `.backends`).
- `.readthedocs.yaml` v2 config so the published site at
  https://djangordf.readthedocs.io/ tracks the released version.
- `docs/requirements.txt` pinning Sphinx ≥ 7, Furo, MyST-Parser,
  sphinx-autodoc-typehints.

### Changed
- `setup.py` re-adds `"Documentation": "https://djangordf.readthedocs.io/"`
  to `project_urls` now that the docs site actually exists.
- `README.md` links to the docs site near the top.

## [0.3.0] - 2026-05-28

The RDFModel walking skeleton: a Django-style declarative layer over a
SPARQL 1.1 triple store. Existing `export_model_to_rdf` continues to
work unchanged. See the design spec at
`docs/superpowers/specs/2026-05-22-rdfmodel-walking-skeleton-design.md`.

### Added
- `djangordf.backends`: `TripleStoreBackend` ABC, `InMemoryBackend`
  (rdflib), and `FusekiBackend` (SPARQL 1.1 HTTP).
- `djangordf.conf.get_backend()` reads `DJANGORDF_BACKEND` to construct
  the configured backend.
- `djangordf.models.RDFModel` + `RDFModelMeta` metaclass: `Meta`
  resolution (`class_iri`, `namespace`, `graph_iri`), per-class
  `objects` manager, IRI minting on save, process-wide model registry
  for forward references.
- Property type system: `DataProperty`, `LangStringProperty`,
  `ObjectProperty`, `URIProperty`, and the `LangString` dataclass.
  Each property owns its `to_rdf` / `from_rdf` mapping and supports
  `many=False/True`.
- `djangordf.namespaces.NamespaceRegistry` seeded with `rdf`, `rdfs`,
  `owl`, `xsd`, `skos`, `dct`, `foaf`. New `DJANGORDF_NAMESPACES`
  setting is read by `DjangordfConfig.ready()`.
- `djangordf.skos.DEFAULT_PREDICATES`: implicit SKOS predicate
  assignment in the metaclass for `pref_label`, `alt_label`,
  `hidden_label`, `definition`, `note`, `broader`, `narrower`,
  `related`, `exact_match`, `close_match`, `in_scheme`.
- `djangordf.manager.RDFManager` full CRUD: `create`, `get`, `save`,
  `delete`, `all`, `filter`. Lazy `RDFQuerySet` with `__iter__`,
  `__len__`, `count`, `first`.
- `DJANGORDF_DEFAULT_NAMESPACE` and `DJANGORDF_DEFAULT_GRAPH` settings
  consumed by `_build_meta`.
- `examples/walking_skeleton.py`: executable acceptance script from
  spec §9.
- Twelve named acceptance unit tests in `tests/test_rdfmodel.py`, plus
  a subprocess test that runs the example end-to-end.

### Changed
- `InMemoryBackend.query` returns the underlying `rdflib.Graph` for
  `CONSTRUCT` / `DESCRIBE` (was a `SPARQLResult` proxy with broken
  attribute delegation) so it matches the abstract contract and
  `FusekiBackend`'s behaviour.

### Notes
- Walking-skeleton design decisions worth knowing about: the metaclass
  silently leaves `predicate=None` for properties whose attribute name
  is not in `DEFAULT_PREDICATES` (no `ImproperlyConfigured`);
  `ObjectProperty.from_rdf` returns target-class instances with only
  `iri` set (no recursive hydration); `RDFQuerySet` materialises via
  one `SELECT DISTINCT ?s` plus one `CONSTRUCT` per subject (N+1 by
  design — collapse is a deferred optimisation).

## [0.2.0] - 2026-05-01

### Added
- `djangordf.apps.DjangordfConfig` so the package can be added to `INSTALLED_APPS`.
- `.flake8` configuration (line-length 100).
- `requirements-dev.txt` with `flake8`, `pytest>=9.0.3`, `pytest-django>=4.11`,
  `Django` and `rdflib`.
- `namespace` and `output_dir` keyword arguments for `export_model_to_rdf`.
- `rdf:type` triple for every exported instance, plus namespace prefix
  binding in the generated graph.

### Changed
- Declare runtime dependencies in `install_requires` (`Django>=3.2`,
  `rdflib>=6.0`); previously empty.
- Minimum Python version bumped to 3.8.

### Fixed
- `bool` values are now emitted as `xsd:boolean` instead of `xsd:integer`
  (bool is a subclass of int in Python, so the order of `isinstance` checks
  matters).
- `datetime` values are emitted via `.isoformat()` typed as `xsd:dateTime`.
- `None` field values are skipped instead of emitting empty literals.
- Dump-metadata resource is typed with a class IRI on `rdf:type` instead of
  a string literal (was semantically invalid RDF).
- Unsupported field types now produce a logger warning instead of being
  silently dropped.

### Removed
- `setup_requires=['pytest-runner']` (deprecated since setuptools 58).
- `tests_require` from `setup.py` (deprecated since setuptools 41.5);
  test tooling moved to `requirements-dev.txt`.

### Security
- Resolves Dependabot alert #1: pytest pinned at vulnerable `7.4.4` is
  removed from `setup.py`; dev requirement now `>=9.0.3`
  (GHSA-6w46-j5rx-g56g / CVE-2025-71176, medium severity, tmpdir handling).

## [0.1.1]

Initial published version.
