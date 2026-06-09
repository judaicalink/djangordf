<!--
Thanks for opening a pull request. Please fill in the sections below
so reviewers can understand the change quickly.

- Open PRs against `development` (release PRs target `main`).
- Reference the issue with `Closes #NNN` so it auto-closes on merge.
- Keep commits focused; English commit messages, imperative mood,
  no AI-attribution trailers.
- All three checks must be green: `flake8`, `pytest`, and
  `sphinx-build -W -b html docs docs/_build/html`.
-->

## Summary

<!-- One or two sentences on what changes and why. -->

## What's in this PR

<!-- Bullets per logical change. Mention the public API surface that
moved. -->

## Test plan

- [ ] `flake8 djangordf tests setup.py examples docs/conf.py` clean
- [ ] `pytest -q` green (note new test count if relevant)
- [ ] `sphinx-build -W -b html docs docs/_build/html` clean
- [ ] CI green on Python 3.10, 3.11, 3.12

## Out of scope

<!-- Anything you considered and deliberately did not include in this
PR. Helps reviewers calibrate expectations. -->

## References

<!-- Issue, design spec section, implementation plan, related PRs. -->

Closes #
