# Backend Interface and InMemoryBackend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the abstract `TripleStoreBackend` interface, an `InMemoryBackend` implementation backed by rdflib, and a `get_backend()` factory that reads Django settings — closing GitHub issue #4.

**Architecture:** A small `djangordf/backends/` package with `base.py` (ABC) and `memory.py` (rdflib `Dataset(default_union=True)` wrapper). A separate `djangordf/conf.py` module owns the settings-to-backend factory so backends do not depend on Django themselves. Tests live under `tests/test_backends.py` and exercise the contract via the in-memory implementation.

**Tech Stack:** Python 3.10+, rdflib 7.x, Django 3.2+, pytest 9.x, pytest-django 4.x.

**Spec reference:** [docs/superpowers/specs/2026-05-22-rdfmodel-walking-skeleton-design.md](../specs/2026-05-22-rdfmodel-walking-skeleton-design.md) §3, §4.

**Issue:** [#4 Backend interface and InMemoryBackend](https://github.com/judaicalink/djangordf/issues/4).

---

## File structure

| File | Responsibility |
|---|---|
| `djangordf/backends/__init__.py` | Public re-exports: `TripleStoreBackend`, `InMemoryBackend` |
| `djangordf/backends/base.py` | `TripleStoreBackend` abstract base class |
| `djangordf/backends/memory.py` | `InMemoryBackend` (rdflib `Dataset(default_union=True)` wrapper) |
| `djangordf/conf.py` | `get_backend()` factory reading `settings.DJANGORDF_BACKEND` |
| `djangordf/__init__.py` | Re-export `TripleStoreBackend`, `InMemoryBackend`, `get_backend` (modify) |
| `tests/test_backends.py` | Unit tests for both interface and InMemoryBackend |
| `tests/test_conf.py` | Unit tests for `get_backend()` factory |
| `tests/settings.py` | Add default `DJANGORDF_BACKEND` setting (modify) |

---

## Task 1: Abstract TripleStoreBackend base class

**Files:**
- Create: `djangordf/backends/__init__.py`
- Create: `djangordf/backends/base.py`
- Create: `tests/test_backends.py`

- [ ] **Step 1.1: Write the failing test**

Create `tests/test_backends.py` with:

```python
"""Tests for djangordf.backends."""
import pytest


def test_triple_store_backend_is_abstract():
    """Instantiating the abstract base must raise TypeError."""
    from djangordf.backends.base import TripleStoreBackend
    with pytest.raises(TypeError):
        TripleStoreBackend()


def test_subclass_must_implement_all_methods():
    """A subclass missing any abstract method cannot be instantiated."""
    from djangordf.backends.base import TripleStoreBackend

    class Partial(TripleStoreBackend):
        def query(self, sparql):
            return None

    with pytest.raises(TypeError):
        Partial()


def test_complete_subclass_can_be_instantiated():
    """A subclass overriding every abstract method works."""
    from djangordf.backends.base import TripleStoreBackend

    class Complete(TripleStoreBackend):
        def query(self, sparql):
            return None

        def update(self, sparql):
            return None

        def add(self, triples, graph=None):
            return None

        def remove(self, pattern, graph=None):
            return None

        def clear(self, graph=None):
            return None

    Complete()  # must not raise
```

- [ ] **Step 1.2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_backends.py -v`
Expected: All three tests fail with `ModuleNotFoundError: No module named 'djangordf.backends'`.

- [ ] **Step 1.3: Create the package and the abstract base**

Create `djangordf/backends/__init__.py`:

```python
"""Triple-store backend abstraction for djangordf."""
from .base import TripleStoreBackend

__all__ = ["TripleStoreBackend"]
```

Create `djangordf/backends/base.py`:

```python
"""Abstract base class every triple-store backend must implement."""
from abc import ABC, abstractmethod
from typing import Iterable, Optional, Tuple

from rdflib import URIRef
from rdflib.graph import Graph
from rdflib.query import Result


Triple = Tuple[object, object, object]
TriplePattern = Tuple[Optional[object], Optional[object], Optional[object]]


class TripleStoreBackend(ABC):
    """The contract a triple-store backend must fulfil.

    Intentionally narrow: SPARQL 1.1 query and update plus convenience
    helpers for bulk add, pattern-based remove, and clearing a graph.
    Anything beyond (transactions, reasoning, named-graph listing) is
    opt-in via subclass extension.
    """

    @abstractmethod
    def query(self, sparql: str) -> Result | Graph:
        """Run a SPARQL SELECT, ASK, CONSTRUCT or DESCRIBE.

        Returns an rdflib ``Graph`` for CONSTRUCT/DESCRIBE and an
        rdflib ``Result`` for SELECT/ASK.
        """

    @abstractmethod
    def update(self, sparql: str) -> None:
        """Run a SPARQL UPDATE (INSERT, DELETE, CLEAR, LOAD)."""

    @abstractmethod
    def add(
        self,
        triples: Iterable[Triple],
        graph: Optional[URIRef] = None,
    ) -> None:
        """Bulk-add triples to a named graph, or the default graph if
        ``graph`` is ``None``."""

    @abstractmethod
    def remove(
        self,
        pattern: TriplePattern,
        graph: Optional[URIRef] = None,
    ) -> None:
        """Remove all triples matching ``(s, p, o)`` where any element
        may be ``None`` to act as a wildcard."""

    @abstractmethod
    def clear(self, graph: Optional[URIRef] = None) -> None:
        """Remove all triples from a named graph, or from the default
        graph if ``graph`` is ``None``."""
```

- [ ] **Step 1.4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_backends.py -v`
Expected: All three tests pass.

- [ ] **Step 1.5: Run flake8**

Run: `.venv/bin/flake8 djangordf tests`
Expected: clean exit.

- [ ] **Step 1.6: Commit**

```bash
git add djangordf/backends/__init__.py djangordf/backends/base.py tests/test_backends.py
git commit -m "Add TripleStoreBackend abstract base"
```

---

## Task 2: InMemoryBackend implementation

**Files:**
- Create: `djangordf/backends/memory.py`
- Modify: `djangordf/backends/__init__.py` (add export)
- Modify: `tests/test_backends.py` (add backend behaviour tests)

- [ ] **Step 2.1: Write the failing tests**

Append to `tests/test_backends.py`:

```python
from rdflib import Literal, URIRef


EX_S = URIRef("http://example.org/s")
EX_P = URIRef("http://example.org/p")
EX_P2 = URIRef("http://example.org/p2")
EX_G = URIRef("http://example.org/g")


@pytest.fixture
def backend():
    from djangordf.backends.memory import InMemoryBackend
    return InMemoryBackend()


def test_in_memory_backend_starts_empty(backend):
    result = backend.query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    assert len(result) == 0


def test_add_then_construct_roundtrips_triples(backend):
    backend.add([(EX_S, EX_P, Literal("v"))])
    result = backend.query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    assert (EX_S, EX_P, Literal("v")) in result


def test_update_insert_data(backend):
    backend.update(
        'INSERT DATA { <http://example.org/s> <http://example.org/p> "v" }'
    )
    result = backend.query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    assert len(result) == 1


def test_update_delete_where(backend):
    backend.add([(EX_S, EX_P, Literal("v"))])
    backend.update("DELETE WHERE { ?s ?p ?o }")
    result = backend.query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    assert len(result) == 0


def test_remove_with_subject_pattern_strips_all_matches(backend):
    backend.add([(EX_S, EX_P, Literal("a"))])
    backend.add([(EX_S, EX_P2, Literal("b"))])
    backend.add([(URIRef("http://example.org/other"), EX_P, Literal("c"))])
    backend.remove((EX_S, None, None))
    result = backend.query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    assert len(result) == 1


def test_clear_default_graph_empties_it(backend):
    backend.add([(EX_S, EX_P, Literal("v"))])
    backend.clear()
    result = backend.query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    assert len(result) == 0


def test_named_graph_is_isolated_from_default(backend):
    backend.add([(EX_S, EX_P, Literal("default"))])
    backend.add([(EX_S, EX_P, Literal("named"))], graph=EX_G)

    in_named = backend.query(
        "CONSTRUCT { ?s ?p ?o } WHERE { "
        "GRAPH <http://example.org/g> { ?s ?p ?o } }"
    )
    assert (EX_S, EX_P, Literal("named")) in in_named
    assert (EX_S, EX_P, Literal("default")) not in in_named


def test_clear_named_graph_leaves_default_intact(backend):
    backend.add([(EX_S, EX_P, Literal("default"))])
    backend.add([(EX_S, EX_P, Literal("named"))], graph=EX_G)
    backend.clear(graph=EX_G)

    everything = backend.query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    assert (EX_S, EX_P, Literal("default")) in everything
    assert (EX_S, EX_P, Literal("named")) not in everything


def test_select_query_returns_bindings(backend):
    backend.add([(EX_S, EX_P, Literal("hello"))])
    rows = list(backend.query("SELECT ?o WHERE { ?s ?p ?o }"))
    assert len(rows) == 1
    assert str(rows[0][0]) == "hello"


def test_ask_query_returns_boolean(backend):
    backend.add([(EX_S, EX_P, Literal("v"))])
    result = backend.query("ASK { ?s ?p ?o }")
    assert bool(result) is True
```

- [ ] **Step 2.2: Run the new tests to verify they fail**

Run: `.venv/bin/pytest tests/test_backends.py -v`
Expected: the new tests fail with `ModuleNotFoundError: No module named 'djangordf.backends.memory'`.

- [ ] **Step 2.3: Implement InMemoryBackend**

Create `djangordf/backends/memory.py`:

```python
"""In-memory triple-store backend using rdflib's Dataset."""
from typing import Iterable, Optional

from rdflib import Dataset, URIRef
from rdflib.graph import Graph
from rdflib.query import Result

from .base import Triple, TriplePattern, TripleStoreBackend


class InMemoryBackend(TripleStoreBackend):
    """Triple-store backend that keeps all data in process memory.

    Powers unit tests and the local quickstart. SPARQL queries and
    updates are dispatched directly to rdflib's own engine.
    """

    def __init__(self) -> None:
        self._store = Dataset(default_union=True)

    def query(self, sparql: str) -> Result | Graph:
        return self._store.query(sparql)

    def update(self, sparql: str) -> None:
        self._store.update(sparql)

    def add(
        self,
        triples: Iterable[Triple],
        graph: Optional[URIRef] = None,
    ) -> None:
        target = self._target(graph)
        for triple in triples:
            target.add(triple)

    def remove(
        self,
        pattern: TriplePattern,
        graph: Optional[URIRef] = None,
    ) -> None:
        self._target(graph).remove(pattern)

    def clear(self, graph: Optional[URIRef] = None) -> None:
        self._target(graph).remove((None, None, None))

    def _target(self, graph: Optional[URIRef]) -> Graph:
        if graph is None:
            if hasattr(self._store, "default_graph"):
                return self._store.default_graph
            return self._store.default_context
        return self._store.get_context(graph)
```

- [ ] **Step 2.4: Re-export from package init**

Edit `djangordf/backends/__init__.py`:

```python
"""Triple-store backend abstraction for djangordf."""
from .base import TripleStoreBackend
from .memory import InMemoryBackend

__all__ = ["TripleStoreBackend", "InMemoryBackend"]
```

- [ ] **Step 2.5: Run all backend tests to verify they pass**

Run: `.venv/bin/pytest tests/test_backends.py -v`
Expected: all tests pass.

- [ ] **Step 2.6: Run flake8**

Run: `.venv/bin/flake8 djangordf tests`
Expected: clean exit.

- [ ] **Step 2.7: Commit**

```bash
git add djangordf/backends/memory.py djangordf/backends/__init__.py tests/test_backends.py
git commit -m "Add InMemoryBackend for the triple-store interface"
```

---

## Task 3: get_backend() factory in djangordf.conf

**Files:**
- Create: `djangordf/conf.py`
- Create: `tests/test_conf.py`
- Modify: `tests/settings.py` (add default `DJANGORDF_BACKEND`)

- [ ] **Step 3.1: Write the failing tests**

Create `tests/test_conf.py`:

```python
"""Tests for djangordf.conf."""
import pytest


def test_get_backend_returns_in_memory_by_default(settings):
    """With no DJANGORDF_BACKEND configured, the factory must fall
    back to the in-memory backend so a quickstart works without any
    Django configuration."""
    if hasattr(settings, "DJANGORDF_BACKEND"):
        del settings.DJANGORDF_BACKEND
    from djangordf.conf import get_backend
    from djangordf.backends.memory import InMemoryBackend
    backend = get_backend()
    assert isinstance(backend, InMemoryBackend)


def test_get_backend_resolves_dotted_class_path(settings):
    settings.DJANGORDF_BACKEND = {
        "class": "djangordf.backends.memory.InMemoryBackend",
    }
    from djangordf.conf import get_backend
    from djangordf.backends.memory import InMemoryBackend
    backend = get_backend()
    assert isinstance(backend, InMemoryBackend)


def test_get_backend_passes_extra_kwargs_to_backend(settings):
    """Settings keys other than ``class`` are forwarded as kwargs."""
    settings.DJANGORDF_BACKEND = {
        "class": "tests.test_conf.RecordingBackend",
        "endpoint": "http://example.org/sparql",
        "user": "alice",
    }
    from djangordf.conf import get_backend
    backend = get_backend()
    assert backend.kwargs == {
        "endpoint": "http://example.org/sparql",
        "user": "alice",
    }


def test_get_backend_raises_for_bad_dotted_path(settings):
    settings.DJANGORDF_BACKEND = {"class": "no.such.module.Class"}
    from djangordf.conf import get_backend
    from django.core.exceptions import ImproperlyConfigured
    with pytest.raises(ImproperlyConfigured):
        get_backend()


# Helper backend used by the kwargs-forwarding test above.
from djangordf.backends.base import TripleStoreBackend  # noqa: E402


class RecordingBackend(TripleStoreBackend):
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def query(self, sparql):
        return None

    def update(self, sparql):
        return None

    def add(self, triples, graph=None):
        return None

    def remove(self, pattern, graph=None):
        return None

    def clear(self, graph=None):
        return None
```

- [ ] **Step 3.2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_conf.py -v`
Expected: tests fail with `ModuleNotFoundError: No module named 'djangordf.conf'`.

- [ ] **Step 3.3: Implement djangordf/conf.py**

Create `djangordf/conf.py`:

```python
"""Settings-driven configuration helpers for djangordf."""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from .backends.base import TripleStoreBackend
from .backends.memory import InMemoryBackend


_DEFAULT_BACKEND_CLASS = (
    "djangordf.backends.memory.InMemoryBackend"
)


def get_backend() -> TripleStoreBackend:
    """Build a triple-store backend instance from Django settings.

    Reads ``settings.DJANGORDF_BACKEND``, expected to be a dict with at
    least a ``class`` key holding a dotted import path. Any other keys
    are forwarded as keyword arguments to the backend's constructor.
    Falls back to the in-memory backend if no setting is configured,
    so importing djangordf in a fresh Django project just works.
    """
    config = getattr(settings, "DJANGORDF_BACKEND", None)
    if config is None:
        return InMemoryBackend()

    dotted = config.get("class", _DEFAULT_BACKEND_CLASS)
    try:
        backend_cls = import_string(dotted)
    except ImportError as exc:
        raise ImproperlyConfigured(
            f"DJANGORDF_BACKEND['class']={dotted!r} cannot be imported: {exc}"
        ) from exc

    kwargs = {k: v for k, v in config.items() if k != "class"}
    return backend_cls(**kwargs)
```

- [ ] **Step 3.4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_conf.py -v`
Expected: all four tests pass.

- [ ] **Step 3.5: Run flake8**

Run: `.venv/bin/flake8 djangordf tests`
Expected: clean exit.

- [ ] **Step 3.6: Commit**

```bash
git add djangordf/conf.py tests/test_conf.py
git commit -m "Add get_backend() factory reading DJANGORDF_BACKEND setting"
```

---

## Task 4: Public re-exports and a configured test default

**Files:**
- Modify: `djangordf/__init__.py`
- Modify: `tests/settings.py`

- [ ] **Step 4.1: Update djangordf/__init__.py**

Replace the contents of `djangordf/__init__.py` with:

```python
from .backends import InMemoryBackend, TripleStoreBackend
from .conf import get_backend
from .functions import export_model_to_rdf

__all__ = [
    "InMemoryBackend",
    "TripleStoreBackend",
    "export_model_to_rdf",
    "get_backend",
]
```

- [ ] **Step 4.2: Add the default backend setting for the test suite**

Edit `tests/settings.py`, adding (after the existing settings, keeping `BASE_DIR`, `SECRET_KEY`, etc. untouched):

```python
DJANGORDF_BACKEND = {
    "class": "djangordf.backends.memory.InMemoryBackend",
}
```

- [ ] **Step 4.3: Run the full test suite**

Run: `.venv/bin/pytest -v`
Expected: every test passes, including the existing `tests/test_export.py` suite.

- [ ] **Step 4.4: Run flake8**

Run: `.venv/bin/flake8 djangordf tests setup.py`
Expected: clean exit.

- [ ] **Step 4.5: Commit**

```bash
git add djangordf/__init__.py tests/settings.py
git commit -m "Re-export backend API and configure default backend for tests"
```

---

## Task 5: Push branch and open the pull request

**Files:** none, only git/gh operations.

- [ ] **Step 5.1: Push the branch**

Run: `git push -u origin feature/backend-interface`
Expected: branch created on remote, tracking established.

- [ ] **Step 5.2: Open the pull request closing issue #4**

Run:

```bash
gh pr create \
  --base development \
  --head feature/backend-interface \
  --title "Add triple-store backend interface and InMemoryBackend" \
  --body "$(cat <<'EOF'
## Summary

Lands the abstract `TripleStoreBackend` interface, the `InMemoryBackend` rdflib implementation, and the `get_backend()` factory that reads `settings.DJANGORDF_BACKEND`. First component of the §4 walking skeleton.

## Files

- `djangordf/backends/base.py` — `TripleStoreBackend` abstract base
- `djangordf/backends/memory.py` — `InMemoryBackend` (rdflib `Dataset(default_union=True)`)
- `djangordf/conf.py` — `get_backend()` factory
- `djangordf/__init__.py` — re-exports the new public API
- `tests/test_backends.py` — interface and behaviour tests
- `tests/test_conf.py` — factory tests
- `tests/settings.py` — default `DJANGORDF_BACKEND` for the test suite

## Test plan

- [x] `flake8 djangordf tests setup.py` clean
- [x] full pytest suite green locally
- [ ] CI green on Python 3.10, 3.11, 3.12

## Reference

Design spec [§3, §4](docs/superpowers/specs/2026-05-22-rdfmodel-walking-skeleton-design.md).

Closes #4.
EOF
)"
```

- [ ] **Step 5.3: Wait for CI to complete**

Run (in the background):

```bash
until [ "$(gh pr view --json statusCheckRollup --jq '[.statusCheckRollup[]] | length')" -gt 0 ] && \
      [ "$(gh pr view --json statusCheckRollup --jq '[.statusCheckRollup[] | select(.status != "COMPLETED")] | length')" -eq 0 ]; do
    sleep 15
done
gh pr view --json statusCheckRollup --jq '[.statusCheckRollup[] | {name, conclusion}]'
```

Expected: all three matrix entries (`test (3.10)`, `test (3.11)`, `test (3.12)`) show `SUCCESS`.

- [ ] **Step 5.4: Stop**

Hand the PR back to the user for merge. Do not merge yourself.

---

## Self-review notes

- Spec §3 module layout — covered by `djangordf/backends/`, `djangordf/conf.py`.
- Spec §4 backend interface (`query`, `update`, `add`, `remove`, `clear`) — covered by Task 1.
- Spec §4 `InMemoryBackend` — covered by Task 2 with named-graph isolation and SELECT/ASK/CONSTRUCT/UPDATE coverage.
- Spec §4 `get_backend()` from `settings.DJANGORDF_BACKEND`, default = in-memory — covered by Task 3.
- Spec §4 out-of-scope (transactions, async, auth) — explicitly not implemented, no tasks added.
- All commit messages, code comments and PR body are English.
- Branch name `feature/backend-interface` follows the project's branch-naming convention.
- No placeholders or "TBD"; every step shows the actual code or command.
