# FusekiBackend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `FusekiBackend`, a SPARQL 1.1 HTTP triple-store backend that conforms to the `TripleStoreBackend` interface and works against Apache Jena Fuseki (and any other SPARQL-1.1-HTTP-conformant store) — closing GitHub issue #5.

**Architecture:** A `FusekiBackend` class that holds a `requests.Session`. `query()` and `update()` POST to the configured endpoint with `application/sparql-query` / `application/sparql-update` content types. `add()` / `remove()` / `clear()` build SPARQL strings and route through `update()`. Unit tests mock `requests.Session.post` (using `unittest.mock`); a single end-to-end integration test sits behind a `@pytest.mark.fuseki` marker that is default-excluded from CI.

**Tech Stack:** `requests` 2.25+, rdflib 7.x, pytest 9.x, Django 3.2+, optionally Docker for local integration testing.

**Spec reference:** [docs/superpowers/specs/2026-05-22-rdfmodel-walking-skeleton-design.md](../specs/2026-05-22-rdfmodel-walking-skeleton-design.md) §4.

**Issue:** [#5 FusekiBackend (SPARQL 1.1 HTTP)](https://github.com/judaicalink/djangordf/issues/5).

---

## File structure

| File | Responsibility |
|---|---|
| `djangordf/backends/fuseki.py` | `FusekiBackend` class with `query`, `update`, `add`, `remove`, `clear`; SPARQL-string helpers |
| `djangordf/backends/__init__.py` | Add `FusekiBackend` to re-exports (modify) |
| `djangordf/__init__.py` | Add `FusekiBackend` to top-level re-exports (modify) |
| `setup.py` | Add `requests` to `install_requires` (modify) |
| `requirements-dev.txt` | Add `requests` (already pulled transitively, but pin) (modify) |
| `pytest.ini` | Register `fuseki` marker and exclude it from default runs (modify) |
| `tests/test_fuseki_backend.py` | Unit tests with `unittest.mock` + one fuseki-marked integration test |
| `docker-compose.yml` | Local Fuseki service for integration tests |

---

## Task 1: Add requests dependency and pytest marker config

**Files:**
- Modify: `setup.py`
- Modify: `requirements-dev.txt`
- Modify: `pytest.ini`

- [ ] **Step 1.1: Add requests to install_requires**

Edit `setup.py`:

```python
    install_requires=[
        "Django>=3.2",
        "rdflib>=6.0",
        "requests>=2.25",
    ],
```

- [ ] **Step 1.2: Pin requests in requirements-dev.txt**

Edit `requirements-dev.txt` to add `requests>=2.25` (one new line, alphabetic order doesn't matter for this file):

```
Django>=3.2
rdflib>=6.0
requests>=2.25
flake8>=6.0
pytest>=9.0.3
pytest-django>=4.11
```

- [ ] **Step 1.3: Register fuseki marker and default-exclude it**

Edit `pytest.ini`:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = tests.settings
python_files = test_*.py
testpaths = tests
pythonpath = .
addopts = -ra -m "not fuseki"
markers =
    fuseki: integration test that requires a running Fuseki instance
```

- [ ] **Step 1.4: Install the new dep into the venv**

Run: `.venv/bin/pip install -r requirements-dev.txt`
Expected: clean install (or "Requirement already satisfied" lines for everything except requests).

- [ ] **Step 1.5: Run the existing suite to make sure nothing broke**

Run: `.venv/bin/pytest -v`
Expected: 28/28 passed, no new warnings, no marker-related errors.

- [ ] **Step 1.6: Commit**

```bash
git add setup.py requirements-dev.txt pytest.ini
git commit -m "Declare requests dependency and register fuseki pytest marker"
```

---

## Task 2: FusekiBackend constructor

**Files:**
- Create: `djangordf/backends/fuseki.py`
- Create: `tests/test_fuseki_backend.py`

- [ ] **Step 2.1: Write the failing test**

Create `tests/test_fuseki_backend.py`:

```python
"""Tests for djangordf.backends.fuseki."""
from unittest import mock

import pytest


def test_construct_stores_endpoint():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    assert backend.endpoint == "http://example.org/sparql"


def test_endpoint_is_normalised_without_trailing_slash():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql/")
    assert backend.endpoint == "http://example.org/sparql"


def test_basic_auth_is_configured_on_session_when_credentials_given():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(
        endpoint="http://example.org/sparql",
        user="alice",
        password="secret",
    )
    assert backend.session.auth == ("alice", "secret")


def test_no_auth_when_credentials_missing():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    assert backend.session.auth is None
```

- [ ] **Step 2.2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_fuseki_backend.py -v`
Expected: all four fail with `ModuleNotFoundError: No module named 'djangordf.backends.fuseki'`.

- [ ] **Step 2.3: Implement the constructor**

Create `djangordf/backends/fuseki.py`:

```python
"""SPARQL 1.1 HTTP triple-store backend for Apache Jena Fuseki and similar."""
from typing import Optional

import requests

from .base import TripleStoreBackend


class FusekiBackend(TripleStoreBackend):
    """Triple-store backend that talks SPARQL 1.1 HTTP to a remote endpoint.

    Compatible with Apache Jena Fuseki and any other store that implements
    the SPARQL 1.1 Protocol (Blazegraph, GraphDB, Stardog).
    """

    def __init__(
        self,
        endpoint: str,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.session = requests.Session()
        if user is not None and password is not None:
            self.session.auth = (user, password)

    # Abstract methods are filled in by later tasks; placeholders raise
    # NotImplementedError so the class can still be instantiated and the
    # constructor is testable independently.
    def query(self, sparql):
        raise NotImplementedError

    def update(self, sparql):
        raise NotImplementedError

    def add(self, triples, graph=None):
        raise NotImplementedError

    def remove(self, pattern, graph=None):
        raise NotImplementedError

    def clear(self, graph=None):
        raise NotImplementedError
```

- [ ] **Step 2.4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_fuseki_backend.py -v`
Expected: all four pass.

- [ ] **Step 2.5: Run flake8**

Run: `.venv/bin/flake8 djangordf tests`
Expected: clean exit.

- [ ] **Step 2.6: Commit**

```bash
git add djangordf/backends/fuseki.py tests/test_fuseki_backend.py
git commit -m "Add FusekiBackend constructor and HTTP session setup"
```

---

## Task 3: query() implementation with CONSTRUCT / SELECT / ASK support

**Files:**
- Modify: `djangordf/backends/fuseki.py`
- Modify: `tests/test_fuseki_backend.py`

- [ ] **Step 3.1: Append the failing tests**

Append to `tests/test_fuseki_backend.py`:

```python
from io import BytesIO

from rdflib import Literal, URIRef


def _mock_response(status=200, text="", content=None, content_type="text/plain"):
    response = mock.Mock()
    response.status_code = status
    response.text = text
    response.content = content if content is not None else text.encode("utf-8")
    response.headers = {"Content-Type": content_type}
    response.raise_for_status = mock.Mock()
    return response


def test_construct_query_posts_to_query_endpoint_with_turtle_accept():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    turtle = (
        "<http://example.org/s> <http://example.org/p> "
        "<http://example.org/o> ."
    )
    with mock.patch.object(
        backend.session, "post",
        return_value=_mock_response(
            text=turtle, content_type="text/turtle",
        ),
    ) as post:
        result = backend.query("CONSTRUCT WHERE { ?s ?p ?o }")

    post.assert_called_once()
    args, kwargs = post.call_args
    assert args[0] == "http://example.org/sparql/query"
    assert kwargs["data"] == "CONSTRUCT WHERE { ?s ?p ?o }"
    assert kwargs["headers"]["Content-Type"] == "application/sparql-query"
    assert "text/turtle" in kwargs["headers"]["Accept"]
    assert (
        URIRef("http://example.org/s"),
        URIRef("http://example.org/p"),
        URIRef("http://example.org/o"),
    ) in result


def test_select_query_returns_parsed_result_bindings():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    json_body = (
        '{"head":{"vars":["o"]},'
        '"results":{"bindings":['
        '{"o":{"type":"literal","value":"hello"}}'
        "]}}"
    )
    with mock.patch.object(
        backend.session, "post",
        return_value=_mock_response(
            text=json_body, content=json_body.encode("utf-8"),
            content_type="application/sparql-results+json",
        ),
    ) as post:
        result = backend.query("SELECT ?o WHERE { ?s ?p ?o }")

    _, kwargs = post.call_args
    assert "application/sparql-results+json" in kwargs["headers"]["Accept"]
    rows = list(result)
    assert len(rows) == 1
    assert str(rows[0][0]) == "hello"


def test_ask_query_returns_boolean():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    json_body = '{"head":{},"boolean":true}'
    with mock.patch.object(
        backend.session, "post",
        return_value=_mock_response(
            text=json_body, content=json_body.encode("utf-8"),
            content_type="application/sparql-results+json",
        ),
    ):
        result = backend.query("ASK { ?s ?p ?o }")
    assert bool(result) is True


def test_query_type_detection_ignores_prefix_declarations():
    """A query with leading PREFIX lines still routes to CONSTRUCT handling."""
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    sparql = (
        "PREFIX ex: <http://example.org/>\n"
        "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"
    )
    with mock.patch.object(
        backend.session, "post",
        return_value=_mock_response(
            text="", content_type="text/turtle",
        ),
    ) as post:
        backend.query(sparql)
    _, kwargs = post.call_args
    assert "text/turtle" in kwargs["headers"]["Accept"]


def test_query_raises_on_http_error():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    bad = _mock_response(status=500, text="boom")
    bad.raise_for_status = mock.Mock(
        side_effect=requests.HTTPError("500")
    )
    with mock.patch.object(backend.session, "post", return_value=bad):
        with pytest.raises(requests.HTTPError):
            backend.query("SELECT ?s WHERE { ?s ?p ?o }")
```

Add `import requests` at the top of the file (we already have `from unittest import mock` from Task 2; keep `pytest` import).

- [ ] **Step 3.2: Run the new tests to verify they fail**

Run: `.venv/bin/pytest tests/test_fuseki_backend.py -v`
Expected: the new five tests fail with `NotImplementedError` from the constructor's stub `query`.

- [ ] **Step 3.3: Implement query()**

Replace the `query` method (and add a private helper) in `djangordf/backends/fuseki.py`:

```python
import re
from io import BytesIO

from rdflib import Graph
from rdflib.query import Result
```

Add at the top imports (next to existing imports), and replace the `query` stub with:

```python
    _QUERY_FORMS = ("CONSTRUCT", "DESCRIBE", "SELECT", "ASK")

    def query(self, sparql):
        form = self._detect_query_form(sparql)
        if form in ("CONSTRUCT", "DESCRIBE"):
            accept = "text/turtle"
        else:
            accept = "application/sparql-results+json"
        response = self._post(
            f"{self.endpoint}/query",
            sparql,
            content_type="application/sparql-query",
            accept=accept,
        )
        if form in ("CONSTRUCT", "DESCRIBE"):
            graph = Graph()
            graph.parse(data=response.text, format="turtle")
            return graph
        return Result.parse(BytesIO(response.content), format="json")

    def _post(self, url, body, content_type, accept):
        response = self.session.post(
            url,
            data=body,
            headers={
                "Content-Type": content_type,
                "Accept": accept,
            },
        )
        response.raise_for_status()
        return response

    @classmethod
    def _detect_query_form(cls, sparql):
        """Pick the first SPARQL query keyword that appears in the string,
        ignoring SPARQL comments and PREFIX/BASE declarations."""
        cleaned = re.sub(r"#[^\n]*", "", sparql).upper()
        for keyword in cls._QUERY_FORMS:
            if re.search(rf"\b{keyword}\b", cleaned):
                return keyword
        raise ValueError("Cannot determine SPARQL query form")
```

- [ ] **Step 3.4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_fuseki_backend.py -v`
Expected: all 9 tests pass.

- [ ] **Step 3.5: Run flake8**

Run: `.venv/bin/flake8 djangordf tests`
Expected: clean exit.

- [ ] **Step 3.6: Commit**

```bash
git add djangordf/backends/fuseki.py tests/test_fuseki_backend.py
git commit -m "Implement FusekiBackend.query() for CONSTRUCT, SELECT and ASK"
```

---

## Task 4: update() implementation

**Files:**
- Modify: `djangordf/backends/fuseki.py`
- Modify: `tests/test_fuseki_backend.py`

- [ ] **Step 4.1: Append the failing tests**

Append to `tests/test_fuseki_backend.py`:

```python
def test_update_posts_to_update_endpoint_with_sparql_update_content_type():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    sparql = (
        'INSERT DATA { <http://example.org/s> <http://example.org/p> "v" }'
    )
    with mock.patch.object(
        backend.session, "post",
        return_value=_mock_response(),
    ) as post:
        backend.update(sparql)
    post.assert_called_once()
    args, kwargs = post.call_args
    assert args[0] == "http://example.org/sparql/update"
    assert kwargs["data"] == sparql
    assert kwargs["headers"]["Content-Type"] == "application/sparql-update"


def test_update_raises_on_http_error():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    bad = _mock_response(status=400, text="bad")
    bad.raise_for_status = mock.Mock(
        side_effect=requests.HTTPError("400")
    )
    with mock.patch.object(backend.session, "post", return_value=bad):
        with pytest.raises(requests.HTTPError):
            backend.update("CLEAR DEFAULT")
```

- [ ] **Step 4.2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_fuseki_backend.py -v`
Expected: the two new tests fail with `NotImplementedError`.

- [ ] **Step 4.3: Implement update()**

Replace the `update` stub in `djangordf/backends/fuseki.py`:

```python
    def update(self, sparql):
        self._post(
            f"{self.endpoint}/update",
            sparql,
            content_type="application/sparql-update",
            accept="*/*",
        )
```

- [ ] **Step 4.4: Run the tests**

Run: `.venv/bin/pytest tests/test_fuseki_backend.py -v`
Expected: all 11 tests pass.

- [ ] **Step 4.5: Run flake8**

Run: `.venv/bin/flake8 djangordf tests`
Expected: clean exit.

- [ ] **Step 4.6: Commit**

```bash
git add djangordf/backends/fuseki.py tests/test_fuseki_backend.py
git commit -m "Implement FusekiBackend.update() over SPARQL 1.1 HTTP"
```

---

## Task 5: add(), remove() and clear() via SPARQL string builders

**Files:**
- Modify: `djangordf/backends/fuseki.py`
- Modify: `tests/test_fuseki_backend.py`

- [ ] **Step 5.1: Append the failing tests**

Append to `tests/test_fuseki_backend.py`:

```python
def _capture_update(backend):
    """Patch update() to record the SPARQL string it would have sent."""
    captured = {}

    def fake_update(sparql):
        captured["sparql"] = sparql

    backend.update = fake_update
    return captured


def test_add_default_graph_emits_insert_data():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    captured = _capture_update(backend)
    backend.add(
        [(
            URIRef("http://example.org/s"),
            URIRef("http://example.org/p"),
            Literal("v"),
        )]
    )
    sparql = captured["sparql"]
    assert "INSERT DATA" in sparql
    assert "<http://example.org/s>" in sparql
    assert "<http://example.org/p>" in sparql
    assert '"v"' in sparql
    assert "GRAPH" not in sparql


def test_add_named_graph_wraps_triples_in_graph_block():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    captured = _capture_update(backend)
    g = URIRef("http://example.org/g")
    backend.add(
        [(
            URIRef("http://example.org/s"),
            URIRef("http://example.org/p"),
            Literal("v"),
        )],
        graph=g,
    )
    sparql = captured["sparql"]
    assert "INSERT DATA" in sparql
    assert "GRAPH <http://example.org/g>" in sparql


def test_add_serialises_typed_literals():
    from djangordf.backends.fuseki import FusekiBackend
    from rdflib.namespace import XSD
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    captured = _capture_update(backend)
    backend.add(
        [(
            URIRef("http://example.org/s"),
            URIRef("http://example.org/p"),
            Literal(42, datatype=XSD.integer),
        )]
    )
    assert "42" in captured["sparql"]
    assert str(XSD.integer) in captured["sparql"]


def test_remove_with_full_triple_emits_delete_where():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    captured = _capture_update(backend)
    backend.remove(
        (
            URIRef("http://example.org/s"),
            URIRef("http://example.org/p"),
            Literal("v"),
        )
    )
    sparql = captured["sparql"]
    assert sparql.startswith("DELETE WHERE")
    assert "<http://example.org/s>" in sparql
    assert "<http://example.org/p>" in sparql


def test_remove_with_wildcards_uses_sparql_variables():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    captured = _capture_update(backend)
    backend.remove((URIRef("http://example.org/s"), None, None))
    sparql = captured["sparql"]
    assert "<http://example.org/s>" in sparql
    assert "?p" in sparql
    assert "?o" in sparql


def test_remove_in_named_graph_wraps_pattern_in_graph_block():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    captured = _capture_update(backend)
    backend.remove(
        (URIRef("http://example.org/s"), None, None),
        graph=URIRef("http://example.org/g"),
    )
    assert "GRAPH <http://example.org/g>" in captured["sparql"]


def test_clear_default_graph_emits_clear_default():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    captured = _capture_update(backend)
    backend.clear()
    assert captured["sparql"] == "CLEAR DEFAULT"


def test_clear_named_graph_emits_clear_silent_graph():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    captured = _capture_update(backend)
    backend.clear(graph=URIRef("http://example.org/g"))
    assert captured["sparql"] == "CLEAR SILENT GRAPH <http://example.org/g>"
```

- [ ] **Step 5.2: Run to verify they fail**

Run: `.venv/bin/pytest tests/test_fuseki_backend.py -v`
Expected: eight new failures with `NotImplementedError`.

- [ ] **Step 5.3: Implement add, remove and clear**

Replace the three stubs in `djangordf/backends/fuseki.py`:

```python
    def add(self, triples, graph=None):
        body = "\n".join(self._format_triple(t) for t in triples)
        if graph is not None:
            sparql = (
                f"INSERT DATA {{ GRAPH <{graph}> {{ {body} }} }}"
            )
        else:
            sparql = f"INSERT DATA {{ {body} }}"
        self.update(sparql)

    def remove(self, pattern, graph=None):
        s, p, o = pattern
        triple = (
            f"{self._term_or_var(s, '?s')} "
            f"{self._term_or_var(p, '?p')} "
            f"{self._term_or_var(o, '?o')} ."
        )
        if graph is not None:
            sparql = (
                f"DELETE WHERE {{ GRAPH <{graph}> {{ {triple} }} }}"
            )
        else:
            sparql = f"DELETE WHERE {{ {triple} }}"
        self.update(sparql)

    def clear(self, graph=None):
        if graph is None:
            self.update("CLEAR DEFAULT")
        else:
            self.update(f"CLEAR SILENT GRAPH <{graph}>")

    @staticmethod
    def _format_triple(triple):
        s, p, o = triple
        return f"{s.n3()} {p.n3()} {o.n3()} ."

    @staticmethod
    def _term_or_var(term, variable):
        return term.n3() if term is not None else variable
```

- [ ] **Step 5.4: Run the tests**

Run: `.venv/bin/pytest tests/test_fuseki_backend.py -v`
Expected: all 19 tests pass.

- [ ] **Step 5.5: Run flake8**

Run: `.venv/bin/flake8 djangordf tests`
Expected: clean exit.

- [ ] **Step 5.6: Commit**

```bash
git add djangordf/backends/fuseki.py tests/test_fuseki_backend.py
git commit -m "Implement FusekiBackend add/remove/clear via SPARQL builders"
```

---

## Task 6: Public re-exports and final-suite verification

**Files:**
- Modify: `djangordf/backends/__init__.py`
- Modify: `djangordf/__init__.py`

- [ ] **Step 6.1: Re-export FusekiBackend from the backends package**

Edit `djangordf/backends/__init__.py`:

```python
"""Triple-store backend abstraction for djangordf."""
from .base import TripleStoreBackend
from .fuseki import FusekiBackend
from .memory import InMemoryBackend

__all__ = ["TripleStoreBackend", "InMemoryBackend", "FusekiBackend"]
```

- [ ] **Step 6.2: Re-export from top-level djangordf**

Edit `djangordf/__init__.py`:

```python
from .backends import FusekiBackend, InMemoryBackend, TripleStoreBackend
from .conf import get_backend
from .functions import export_model_to_rdf

__all__ = [
    "FusekiBackend",
    "InMemoryBackend",
    "TripleStoreBackend",
    "export_model_to_rdf",
    "get_backend",
]
```

- [ ] **Step 6.3: Run the full test suite**

Run: `.venv/bin/pytest -v`
Expected: all tests pass (28 + 19 = 47 total). No `fuseki`-marked tests run by default thanks to `addopts = -ra -m "not fuseki"`.

- [ ] **Step 6.4: Run flake8**

Run: `.venv/bin/flake8 djangordf tests setup.py`
Expected: clean exit.

- [ ] **Step 6.5: Verify the top-level import works**

Run: `.venv/bin/python -c "from djangordf import FusekiBackend; print(FusekiBackend)"`
Expected: `<class 'djangordf.backends.fuseki.FusekiBackend'>`.

- [ ] **Step 6.6: Commit**

```bash
git add djangordf/backends/__init__.py djangordf/__init__.py
git commit -m "Re-export FusekiBackend at package and top level"
```

---

## Task 7: docker-compose + one integration smoke test behind the marker

**Files:**
- Create: `docker-compose.yml`
- Create: `tests/test_fuseki_integration.py`

- [ ] **Step 7.1: Add a Fuseki service for local integration testing**

Create `docker-compose.yml` at the repository root:

```yaml
services:
  fuseki:
    image: stain/jena-fuseki:5.5.0
    container_name: djangordf-fuseki
    ports:
      - "3030:3030"
    environment:
      ADMIN_PASSWORD: admin
      FUSEKI_DATASET_1: ds
```

- [ ] **Step 7.2: Add one integration test gated by the fuseki marker**

Create `tests/test_fuseki_integration.py`:

```python
"""Integration tests for FusekiBackend against a real Fuseki instance.

These tests are marked with ``@pytest.mark.fuseki`` and are excluded by
the default pytest run (see ``pytest.ini``). To run them locally start
the bundled docker-compose Fuseki and call::

    docker compose up -d fuseki
    pytest -m fuseki
"""
import os

import pytest
from rdflib import Literal, URIRef


pytestmark = pytest.mark.fuseki


FUSEKI_ENDPOINT = os.environ.get(
    "DJANGORDF_FUSEKI_ENDPOINT", "http://localhost:3030/ds"
)


@pytest.fixture
def backend():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint=FUSEKI_ENDPOINT)
    backend.clear()
    yield backend
    backend.clear()


def test_roundtrip_against_real_fuseki(backend):
    s = URIRef("http://example.org/s")
    p = URIRef("http://example.org/p")
    o = Literal("hello")
    backend.add([(s, p, o)])
    result = backend.query("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    assert (s, p, o) in result
```

- [ ] **Step 7.3: Verify default pytest run still skips the integration test**

Run: `.venv/bin/pytest -v`
Expected: 47 passed, `tests/test_fuseki_integration.py` is **not** collected (marker excluded).

- [ ] **Step 7.4: Run flake8**

Run: `.venv/bin/flake8 djangordf tests setup.py`
Expected: clean exit.

- [ ] **Step 7.5: Commit**

```bash
git add docker-compose.yml tests/test_fuseki_integration.py
git commit -m "Add docker-compose Fuseki service and a marked integration smoke test"
```

---

## Task 8: Push the branch and open the pull request

**Files:** none, only git/gh operations.

- [ ] **Step 8.1: Push the branch**

Run: `git push -u origin feature/fuseki-backend`
Expected: branch created on remote.

- [ ] **Step 8.2: Open the pull request closing issue #5**

Run:

```bash
gh pr create \
  --base development \
  --head feature/fuseki-backend \
  --title "Add FusekiBackend (SPARQL 1.1 HTTP)" \
  --body "$(cat <<'EOF'
## Summary

Lands the production triple-store backend: `FusekiBackend` talks SPARQL 1.1 HTTP to a remote endpoint (Fuseki, Blazegraph, GraphDB, Stardog). Second component of the §4 walking skeleton.

## Files

- `djangordf/backends/fuseki.py` — `FusekiBackend`
- `djangordf/backends/__init__.py` + `djangordf/__init__.py` — re-exports
- `setup.py`, `requirements-dev.txt` — declare `requests` runtime dependency
- `pytest.ini` — register `fuseki` marker, default-exclude from CI
- `tests/test_fuseki_backend.py` — unit tests (mocked HTTP, 19 tests)
- `tests/test_fuseki_integration.py` — one marker-gated integration smoke test
- `docker-compose.yml` — local Fuseki service for the integration test
- `docs/superpowers/plans/2026-05-22-fuseki-backend.md` — implementation plan

## Test plan

- [x] `flake8 djangordf tests setup.py` clean
- [x] 47/47 unit tests green locally (28 pre-existing + 19 new)
- [x] Integration tests skipped by default; runnable via `docker compose up -d fuseki && pytest -m fuseki`
- [ ] CI green on Python 3.10, 3.11, 3.12

## Notes

`FusekiBackend` and `InMemoryBackend` are interchangeable through the `TripleStoreBackend` contract. Selecting Fuseki at runtime is a settings change:

\`\`\`python
DJANGORDF_BACKEND = {
    "class": "djangordf.backends.fuseki.FusekiBackend",
    "endpoint": "http://localhost:3030/ds",
    "user": "admin",
    "password": "admin",
}
\`\`\`

## Reference

Design spec [§4](docs/superpowers/specs/2026-05-22-rdfmodel-walking-skeleton-design.md).

Closes #5.
EOF
)"
```

- [ ] **Step 8.3: Wait for CI**

Run in the background:

```bash
until [ "$(gh pr view --json statusCheckRollup --jq '[.statusCheckRollup[]] | length')" -gt 0 ] && \
      [ "$(gh pr view --json statusCheckRollup --jq '[.statusCheckRollup[] | select(.status != "COMPLETED")] | length')" -eq 0 ]; do
    sleep 15
done
gh pr view --json statusCheckRollup --jq '[.statusCheckRollup[] | {name, conclusion}]'
```

Expected: all three matrix entries (`test (3.10)`, `test (3.11)`, `test (3.12)`) show `SUCCESS`.

- [ ] **Step 8.4: Stop**

Hand back to the user for review and merge. Do not merge yourself.

---

## Self-review notes

- Spec §4 `FusekiBackend` — covered by Tasks 2–5.
- Spec §4 `requests.Session` keep-alive — covered in Task 2 (Session created once in `__init__`).
- Spec §4 HTTP Basic Auth — covered in Task 2 (auth tuple on the Session).
- Spec §4 `query()` `POST /query` — covered in Task 3.
- Spec §4 `update()` `POST /update` — covered in Task 4.
- Spec §4 `add()` / `remove()` → `INSERT DATA` / `DELETE WHERE` — covered in Task 5.
- Spec §4 marker `@pytest.mark.fuseki`, default-excluded — covered in Task 1 (pytest.ini) and Task 7 (test file).
- Spec §4 SPARQL 1.1 HTTP conformance for non-Fuseki stores — covered implicitly (no Fuseki-specific endpoints used).
- Spec §4 out-of-scope (transactions, async, auth beyond HTTP Basic) — explicitly not implemented.
- All code comments, docstrings, commit messages, PR body and issue body are English.
- Branch name `feature/fuseki-backend` follows the project's convention.
- No placeholders or "TBD"; every step shows the actual code or command.
