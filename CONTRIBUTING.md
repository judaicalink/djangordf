# Contributing to djangordf

Thank you for taking the time to contribute. This document captures
the conventions used in the repository so that issues, branches,
commits, and pull requests stay consistent and easy to review.

## Code of Conduct

Participation in this project is governed by the
[Code of Conduct](CODE_OF_CONDUCT.md). Please read it before
opening issues or pull requests.

## How to report a bug or propose a change

Use the GitHub issue templates:

- **Bug report** — for crashes, incorrect behaviour, regressions.
- **Feature request** — for new functionality or API changes.
- **Question** — for "how do I" / "is this supported" questions
  that don't fit the other two.

Blank issues are disabled to keep the tracker scannable. Pick the
closest template and feel free to delete sections that don't apply.

## Development setup

```bash
git clone https://github.com/judaicalink/djangordf
cd djangordf
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -r docs/requirements.txt    # for the Sphinx build
pip install -e .                         # editable install
```

The test suite uses an in-memory rdflib backend by default and needs
no external services. Optional Fuseki integration tests live behind
`@pytest.mark.fuseki` and require a running Fuseki instance (see the
`docker-compose.yml` at the repository root).

## Running the checks locally

Before opening a pull request, run:

```bash
flake8 djangordf tests setup.py examples docs/conf.py
pytest -q
sphinx-build -W -b html docs docs/_build/html
```

All three must be clean. CI runs the lint and test steps on Python
3.10, 3.11 and 3.12; the Sphinx build is also exercised through the
ReadTheDocs build of `main`.

## Branch and commit conventions

- `main` — released versions. Tags (`vX.Y.Z`) live here. Updates land
  via release PRs from `release/X.Y.Z`.
- `development` — integration branch. Feature, bug-fix, and docs
  branches open their PRs here.
- `feature/<slug>` — new functionality. One feature per branch.
- `bugfix/<slug>` — bug fixes against `development`. Hot-fixes that
  must skip `development` are exceptional; coordinate via the issue.
- `docs/<slug>` — documentation-only changes.
- `release/<version>` — short-lived branches that bump the version
  and the changelog, then merge into `main`.

Commit messages are written in English, imperative mood, and
describe what changes rather than what was added. Keep one logical
change per commit when possible. Do not include AI-attribution
trailers; commit as yourself.

## Pull request flow

1. Open or pick an issue describing the change. Comment on the
   issue to claim it if necessary.
2. Branch off `development` using the naming convention above.
3. Make focused commits. Run `flake8`, `pytest`, and
   `sphinx-build -W` before pushing.
4. Open a pull request against `development`. Use the PR template
   and reference the issue with `Closes #NNN` in the description.
5. CI must be green on Python 3.10/3.11/3.12. Sphinx warnings are
   treated as errors on RTD; please run the strict build locally.
6. A maintainer will review, request changes if needed, and merge.

## Release flow (maintainer reference)

1. Cut `release/X.Y.Z` from `development`. Bump
   `setup.py` and update `CHANGELOG.md` (Keep-a-Changelog format,
   sections `Added`, `Changed`, `Fixed`, `Removed`, `Security`,
   `Notes`).
2. Open a pull request into `main`. After merge, tag the merge commit
   `vX.Y.Z` and create a matching GitHub release.
3. Back-merge `main` into `development` so the version bump and
   changelog flow forward.
4. Upload the new wheel + sdist to PyPI.
5. ReadTheDocs picks up the new tag automatically; verify the docs
   site rebuilt and links resolve.

## Documentation

User-facing documentation lives under `docs/` and is built with
Sphinx + MyST + the Furo theme. The API reference is autodoc-driven,
so docstrings on public symbols matter — keep them concise and
focused on intent.

If your change adds or modifies a public symbol, extend the relevant
page in `docs/api/` (one page per public module) so the doc tree
stays in sync.

## Reference

- Walking-skeleton design spec:
  [`docs/superpowers/specs/2026-05-22-rdfmodel-walking-skeleton-design.md`](docs/superpowers/specs/2026-05-22-rdfmodel-walking-skeleton-design.md)
- Per-issue implementation plans:
  [`docs/superpowers/plans/`](docs/superpowers/plans/)
