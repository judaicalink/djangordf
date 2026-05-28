# Sphinx + ReadTheDocs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a real Sphinx documentation site for djangordf, hosted on ReadTheDocs, so the `Documentation` project URL we used to advertise in `setup.py` resolves to actual reference + quickstart content. Closes GitHub issue #23.

**Architecture:** User-facing docs live at the repository root under `docs/` (alongside the existing `docs/superpowers/` working notes, which Sphinx excludes). Sphinx config + content sources sit in `docs/`; build output goes to `docs/_build/html` (gitignored). MyST is enabled so all sources are Markdown, matching the README and CHANGELOG. Theme is Furo — clean modern look, dark-mode-aware, widely used in the Python ecosystem. The API reference is driven by `autodoc` with explicit `automodule` directives per public module (the public API is small and stable enough that hand-curated entries beat blanket `sphinx-apidoc`). `docs/conf.py` runs `django.setup()` against `tests.settings` before autodoc inspects the package — `RDFModel`'s metaclass reads `settings.DJANGORDF_DEFAULT_NAMESPACE` at import-time, so Django settings must be live. RTD build is configured via `.readthedocs.yaml` v2: Python 3.12, install `requirements-dev.txt` + `docs/requirements.txt`, build HTML.

**Tech stack:** Sphinx ≥ 7, MyST-Parser, Furo, Django (already in `requirements-dev.txt`).

**Issue:** [#23 Sphinx + ReadTheDocs](https://github.com/judaicalink/djangordf/issues/23).

---

## File structure

| Path | Purpose | Action |
|---|---|---|
| `docs/conf.py` | Sphinx configuration | new |
| `docs/index.md` | landing page (welcome, ToC) | new |
| `docs/installation.md` | install + Django setup + Fuseki swap | new |
| `docs/quickstart.md` | the walking-skeleton worked example | new |
| `docs/settings.md` | all `DJANGORDF_*` settings | new |
| `docs/api/index.md` | API reference toc | new |
| `docs/api/models.md` | `djangordf.models` autodoc | new |
| `docs/api/properties.md` | `djangordf.properties` autodoc | new |
| `docs/api/manager.md` | `djangordf.manager` autodoc | new |
| `docs/api/namespaces.md` | `djangordf.namespaces` autodoc | new |
| `docs/api/skos.md` | `djangordf.skos` autodoc | new |
| `docs/api/backends.md` | `djangordf.backends` autodoc | new |
| `docs/requirements.txt` | Sphinx + theme + myst | new |
| `.readthedocs.yaml` | RTD build config (v2) | new |
| `.gitignore` | exclude `docs/_build/` | extend |
| `setup.py` | re-add `Documentation` project URL pointing to `https://djangordf.readthedocs.io/` | edit |
| `README.md` | link to the hosted docs from the install / usage sections | edit |

`docs/superpowers/` keeps living where it is and is added to Sphinx's `exclude_patterns`.

---

## Tasks

### Task 1 — Sphinx skeleton

- [ ] `docs/requirements.txt` pinning: `sphinx>=7,<9`, `furo>=2024.5`, `myst-parser>=2`, `sphinx-autodoc-typehints>=2`.
- [ ] `docs/conf.py`:
      - Set `os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")`, `sys.path.insert(0, repo_root)`, `django.setup()` before any imports of djangordf.
      - `project = "djangordf"`, `author = "Benjamin Schnabel"`, derive `release` from `djangordf` setup metadata (read `setup.py` via `importlib.metadata` if installed; otherwise hardcode "0.3.0" as a fallback).
      - `extensions = ["myst_parser", "sphinx.ext.autodoc", "sphinx.ext.autosummary", "sphinx.ext.intersphinx", "sphinx.ext.viewcode", "sphinx_autodoc_typehints"]`.
      - `html_theme = "furo"`.
      - `intersphinx_mapping` for Python and rdflib.
      - `exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "superpowers"]`.
      - `myst_enable_extensions = ["colon_fence", "deflist"]`.

### Task 2 — Content pages

- [ ] `docs/index.md` — short welcome + ToC linking to installation, quickstart, settings, api/.
- [ ] `docs/installation.md` — `pip install djangordf`, `INSTALLED_APPS`, minimal settings, swap to Fuseki backend block.
- [ ] `docs/quickstart.md` — Term model with `pref_label` + `broader`, create / get / filter, `examples/walking_skeleton.py` reference.
- [ ] `docs/settings.md` — `DJANGORDF_BACKEND`, `DJANGORDF_DEFAULT_NAMESPACE`, `DJANGORDF_DEFAULT_GRAPH`, `DJANGORDF_NAMESPACES` — purpose, default, example.
- [ ] `docs/api/*.md` — one page per public module, each with a short opening paragraph plus an `automodule` MyST directive (`:members:`, `:show-inheritance:`, `:undoc-members: false`).

### Task 3 — RTD config

- [ ] `.readthedocs.yaml`:
      ```yaml
      version: 2
      build:
        os: ubuntu-22.04
        tools:
          python: "3.12"
      python:
        install:
          - requirements: requirements-dev.txt
          - requirements: docs/requirements.txt
          - method: pip
            path: .
      sphinx:
        configuration: docs/conf.py
        fail_on_warning: true
      formats: []
      ```

### Task 4 — Gitignore + setup.py + README

- [ ] `.gitignore`: add `docs/_build/`.
- [ ] `setup.py`: re-add `"Documentation": "https://djangordf.readthedocs.io/"` to `project_urls`.
- [ ] `README.md`: link "see the docs at https://djangordf.readthedocs.io/" near the install / usage sections.

### Task 5 — Local build verification

- [ ] Install docs requirements into the project venv.
- [ ] `sphinx-build -W -b html docs docs/_build/html` exits 0 with no warnings.
- [ ] Spot-check `index.html`, `quickstart.html`, `api/models.html`.

### Task 6 — Lint + tests + push

- [ ] `flake8 djangordf tests setup.py examples docs/conf.py` clean (only `conf.py` is Python in docs/).
- [ ] `pytest -q` unchanged (151/151).
- [ ] Commit per repo convention. Push branch. Open PR against `development` with the RTD link and a screenshot of `index.html` if possible.

---

## Out of scope (recorded for follow-ups)

- Tutorial-style long-form guides ("Build a SKOS thesaurus end-to-end") — separate ergonomics issue.
- Versioned doc builds on RTD (stable / latest / per-tag) — RTD project setting, not a code task; arrange after first build is green.
- Translations.
- Custom Furo branding (favicon, logo, accent colour).

## Done when

- All build artifacts exist and `sphinx-build -W` is green.
- README and `setup.py` both point at `https://djangordf.readthedocs.io/`.
- RTD project linked under `judaicalink/djangordf` builds the `main` branch successfully (manual step after the PR merges).
- PR merged into `development`; issue #23 closed.
