# Changelog

All notable changes to djangordf will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
