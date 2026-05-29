# Changelog

All notable changes to djangordf will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
