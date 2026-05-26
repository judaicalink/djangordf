# RDFModel and Metaclass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land `RDFModel`, its `RDFModelMeta` metaclass, the per-class `Meta` resolution (`class_iri`, `namespace`, `graph_iri` with sensible defaults), IRI minting on save, identity by IRI, the per-subclass `DoesNotExist` exception, and a process-wide model registry — closing GitHub issue #6.

**Architecture:** A small `djangordf/models.py` defines the metaclass and the base class. The metaclass inspects each new subclass for `Property` descriptors (recognised structurally so this task does not depend on the final `Property` API from #7), resolves the inner `Meta` once into `cls._meta`, registers the class so `ObjectProperty("self", ...)` and forward references can resolve later, and attaches a minimal `RDFManager` to `cls.objects` so `MyModel.objects.save(instance)` and `MyModel.objects.delete(instance)` work end-to-end against the configured triple-store backend. Property type definitions and the full manager API (`get`, `all`, `filter`, `RDFQuerySet`) are intentionally minimal stubs here; #7 and #8 will replace them. CURIE resolution (`"skos:Concept"` → `URIRef`) is supported via a tiny in-module SKOS table; the full `NamespaceRegistry` lands in #9.

**Tech Stack:** Python 3.10+, rdflib 7.x, Django 3.2+, pytest 9.x, pytest-django 4.x.

**Spec reference:** [docs/superpowers/specs/2026-05-22-rdfmodel-walking-skeleton-design.md](../specs/2026-05-22-rdfmodel-walking-skeleton-design.md) §5.

**Issue:** [#6 RDFModel base class and metaclass](https://github.com/judaicalink/djangordf/issues/6).

---

## File structure

| File | Responsibility | Final owner |
|---|---|---|
| `djangordf/properties.py` | Minimal `Property` base descriptor — just enough so the metaclass can recognise property declarations. Full property type system replaces this in #7. | this task (stub) |
| `djangordf/skos.py` | `Concept` IRI constant and a tiny `_CURIE_TABLE` for in-module CURIE resolution. Replaced/extended in #9. | this task (stub) |
| `djangordf/manager.py` | Minimal `RDFManager` with `save(instance)` and `delete(instance)` against the configured backend. Full CRUD/queryset API lands in #8. | this task (stub) |
| `djangordf/models.py` | `RDFModelMeta`, `RDFModel`, `_build_meta`, `_MODEL_REGISTRY`, per-subclass `DoesNotExist`. | this task (full) |
| `djangordf/__init__.py` | Re-export `RDFModel`, `Property`. | modify |
| `tests/test_models.py` | Unit tests for the metaclass, `_build_meta`, IRI minting, identity, `DoesNotExist`, save/delete round-trip via `InMemoryBackend`. | new |

---

## Task 1: Minimal Property descriptor

**Files:**
- Create: `djangordf/properties.py`
- Create: `tests/test_properties.py`

- [ ] **Step 1.1: Write the failing test**

Create `tests/test_properties.py`:

```python
"""Tests for djangordf.properties (minimal base in this milestone)."""
from rdflib import URIRef


def test_property_stores_predicate():
    from djangordf.properties import Property
    p = Property(predicate=URIRef("http://example.org/p"))
    assert p.predicate == URIRef("http://example.org/p")


def test_property_predicate_defaults_to_none():
    from djangordf.properties import Property
    p = Property()
    assert p.predicate is None


def test_contribute_to_class_records_attribute_name():
    from djangordf.properties import Property
    p = Property()
    p.contribute_to_class("pref_label")
    assert p.attr_name == "pref_label"
```

- [ ] **Step 1.2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_properties.py -v`
Expected: all three fail with `ModuleNotFoundError: No module named 'djangordf.properties'`.

- [ ] **Step 1.3: Implement the minimal Property base**

Create `djangordf/properties.py`:

```python
"""Declarative property descriptors for RDFModel.

Only the bare minimum that the metaclass needs to recognise a property
declaration lives here. The full type system (DataProperty,
LangStringProperty, ObjectProperty, URIProperty) is implemented in
issue #7.
"""
from typing import Optional

from rdflib import URIRef


class Property:
    """Base class for declarative property descriptors."""

    def __init__(
        self,
        predicate: Optional[URIRef] = None,
        *,
        many: bool = False,
        required: bool = False,
        default=None,
    ) -> None:
        self.predicate = URIRef(predicate) if predicate is not None else None
        self.many = many
        self.required = required
        self._default = default
        self.attr_name: Optional[str] = None

    def contribute_to_class(self, attr_name: str) -> None:
        self.attr_name = attr_name

    def default(self):
        if self.many:
            return []
        return self._default
```

- [ ] **Step 1.4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_properties.py -v`
Expected: 3 passed.

- [ ] **Step 1.5: Run flake8**

Run: `.venv/bin/flake8 djangordf tests`
Expected: clean.

- [ ] **Step 1.6: Commit**

```bash
git add djangordf/properties.py tests/test_properties.py
git commit -m "Add minimal Property descriptor base for the metaclass"
```

---

## Task 2: SKOS class IRI and CURIE table

**Files:**
- Create: `djangordf/skos.py`
- Create: `tests/test_skos.py`

- [ ] **Step 2.1: Write the failing test**

Create `tests/test_skos.py`:

```python
"""Tests for djangordf.skos (minimal CURIE table in this milestone)."""
from rdflib.namespace import SKOS


def test_skos_concept_constant():
    from djangordf.skos import Concept
    assert Concept == SKOS.Concept


def test_resolve_curie_known_prefix():
    from djangordf.skos import resolve_curie
    assert resolve_curie("skos:Concept") == SKOS.Concept


def test_resolve_curie_passes_full_iri_through():
    from djangordf.skos import resolve_curie
    iri = "http://example.org/Person"
    assert str(resolve_curie(iri)) == iri


def test_resolve_curie_unknown_prefix_raises():
    import pytest
    from djangordf.skos import resolve_curie
    with pytest.raises(ValueError):
        resolve_curie("xxx:Thing")
```

- [ ] **Step 2.2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_skos.py -v`
Expected: all four fail with `ModuleNotFoundError: No module named 'djangordf.skos'`.

- [ ] **Step 2.3: Implement the minimal skos module**

Create `djangordf/skos.py`:

```python
"""SKOS class IRI and CURIE resolution for the RDFModel default meta.

A full ``NamespaceRegistry`` is implemented in issue #9; this module
ships only the constants the metaclass and ``_build_meta`` need so #6
can be merged on its own.
"""
from rdflib import URIRef
from rdflib.namespace import RDF, RDFS, SKOS, XSD


Concept = SKOS.Concept


_CURIE_TABLE = {
    "skos": SKOS,
    "rdf": RDF,
    "rdfs": RDFS,
    "xsd": XSD,
}


def resolve_curie(value) -> URIRef:
    """Turn a CURIE (``skos:Concept``) or a full IRI into a ``URIRef``.

    Full IRIs (``http://``, ``https://``, ``urn:``) pass straight
    through. Unknown prefixes raise ``ValueError`` so misconfiguration
    is loud.
    """
    if isinstance(value, URIRef):
        return value
    if not isinstance(value, str):
        raise TypeError(f"Cannot resolve {value!r} as CURIE or IRI")

    if value.startswith(("http://", "https://", "urn:")):
        return URIRef(value)
    if ":" in value:
        prefix, local = value.split(":", 1)
        if prefix in _CURIE_TABLE:
            return URIRef(_CURIE_TABLE[prefix] + local)
        raise ValueError(f"Unknown CURIE prefix: {prefix!r}")
    return URIRef(value)
```

- [ ] **Step 2.4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_skos.py -v`
Expected: 4 passed.

- [ ] **Step 2.5: Run flake8**

Run: `.venv/bin/flake8 djangordf tests`
Expected: clean.

- [ ] **Step 2.6: Commit**

```bash
git add djangordf/skos.py tests/test_skos.py
git commit -m "Add minimal SKOS constants and CURIE resolver"
```

---

## Task 3: Minimal RDFManager for save/delete

**Files:**
- Create: `djangordf/manager.py`
- Create: `tests/test_manager.py`

- [ ] **Step 3.1: Write the failing test**

Create `tests/test_manager.py`:

```python
"""Tests for djangordf.manager (minimal save/delete in this milestone)."""
from unittest import mock

from rdflib import URIRef


class _DummyModel:
    pass


def test_manager_holds_model_reference():
    from djangordf.manager import RDFManager
    m = RDFManager(_DummyModel)
    assert m.model_class is _DummyModel


def test_save_issues_delete_then_insert_via_backend():
    from djangordf.manager import RDFManager

    fake_backend = mock.Mock()

    class FakeModel:
        _meta = mock.Mock(
            graph_iri=URIRef("http://example.org/g"),
            class_iri=URIRef("http://example.org/C"),
        )

        def _to_triples(self):
            return [
                (
                    URIRef("http://example.org/s"),
                    URIRef("http://example.org/p"),
                    URIRef("http://example.org/o"),
                )
            ]

    instance = FakeModel()
    instance.iri = URIRef("http://example.org/s")

    m = RDFManager(FakeModel)
    m._backend = fake_backend
    m.save(instance)

    fake_backend.update.assert_called_once()
    sparql = fake_backend.update.call_args.args[0]
    assert "DELETE" in sparql
    assert "INSERT DATA" in sparql
    assert "<http://example.org/s>" in sparql
    assert "<http://example.org/g>" in sparql


def test_delete_removes_all_triples_for_iri_in_graph():
    from djangordf.manager import RDFManager

    fake_backend = mock.Mock()

    class FakeModel:
        _meta = mock.Mock(graph_iri=URIRef("http://example.org/g"))

    instance = FakeModel()
    instance.iri = URIRef("http://example.org/s")

    m = RDFManager(FakeModel)
    m._backend = fake_backend
    m.delete(instance)

    fake_backend.update.assert_called_once()
    sparql = fake_backend.update.call_args.args[0]
    assert "DELETE" in sparql
    assert "<http://example.org/s>" in sparql
    assert "<http://example.org/g>" in sparql
```

- [ ] **Step 3.2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_manager.py -v`
Expected: all three fail with `ModuleNotFoundError: No module named 'djangordf.manager'`.

- [ ] **Step 3.3: Implement the minimal manager**

Create `djangordf/manager.py`:

```python
"""Default object manager bound to each RDFModel subclass.

This milestone ships only ``save`` and ``delete``. The full CRUD and
queryset API (``get``, ``all``, ``filter``, ``RDFQuerySet``) lands in
issue #8.
"""
from .conf import get_backend


def _term(term):
    return term.n3()


def _format_triple(triple):
    s, p, o = triple
    return f"{_term(s)} {_term(p)} {_term(o)} ."


class RDFManager:
    """Object manager attached to ``cls.objects`` by ``RDFModelMeta``."""

    def __init__(self, model_class):
        self.model_class = model_class
        self._backend = None

    @property
    def backend(self):
        if self._backend is None:
            self._backend = get_backend()
        return self._backend

    def save(self, instance) -> None:
        graph_iri = instance._meta.graph_iri
        iri = instance.iri
        triples = instance._to_triples()
        body = "\n".join(_format_triple(t) for t in triples)
        sparql = (
            f"WITH <{graph_iri}> "
            f"DELETE {{ <{iri}> ?p ?o }} WHERE {{ <{iri}> ?p ?o }} ;"
            f"INSERT DATA {{ GRAPH <{graph_iri}> {{ {body} }} }}"
        )
        self.backend.update(sparql)

    def delete(self, instance) -> None:
        graph_iri = instance._meta.graph_iri
        iri = instance.iri
        sparql = (
            f"WITH <{graph_iri}> "
            f"DELETE {{ <{iri}> ?p ?o }} WHERE {{ <{iri}> ?p ?o }}"
        )
        self.backend.update(sparql)
```

- [ ] **Step 3.4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_manager.py -v`
Expected: 3 passed.

- [ ] **Step 3.5: Run flake8**

Run: `.venv/bin/flake8 djangordf tests`
Expected: clean.

- [ ] **Step 3.6: Commit**

```bash
git add djangordf/manager.py tests/test_manager.py
git commit -m "Add minimal RDFManager with save and delete via SPARQL"
```

---

## Task 4: RDFModel and RDFModelMeta — collection, defaults, registry

**Files:**
- Create: `djangordf/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 4.1: Write the failing test**

Create `tests/test_models.py`:

```python
"""Tests for djangordf.models (RDFModel + RDFModelMeta)."""
from rdflib import URIRef
from rdflib.namespace import SKOS

from djangordf.properties import Property


def _fresh_model_name(monkeypatch):
    """Counter so each test defines a uniquely-named subclass; the
    metaclass registry is process-wide and we do not want name clashes
    across tests."""
    import itertools
    if not hasattr(_fresh_model_name, "_counter"):
        _fresh_model_name._counter = itertools.count(1)
    return f"Model{next(_fresh_model_name._counter)}"


# -- metaclass collection ---------------------------------------------------


def test_metaclass_collects_properties():
    from djangordf.models import RDFModel

    class Term(RDFModel):
        title = Property(predicate=URIRef("http://example.org/title"))

    assert "title" in Term._properties
    assert isinstance(Term._properties["title"], Property)
    assert Term._properties["title"].attr_name == "title"


def test_metaclass_does_not_collect_non_property_attributes():
    from djangordf.models import RDFModel

    class Term(RDFModel):
        title = Property()
        not_a_property = "just a string"

    assert "title" in Term._properties
    assert "not_a_property" not in Term._properties


# -- _build_meta defaults ---------------------------------------------------


def test_default_class_iri_is_skos_concept():
    from djangordf.models import RDFModel

    class Term(RDFModel):
        pass

    assert Term._meta.class_iri == SKOS.Concept


def test_meta_namespace_falls_back_to_urn_default(settings):
    if hasattr(settings, "DJANGORDF_DEFAULT_NAMESPACE"):
        del settings.DJANGORDF_DEFAULT_NAMESPACE
    from djangordf.models import RDFModel

    class Term(RDFModel):
        pass

    assert str(Term._meta.namespace).startswith("urn:djangordf:term:")


def test_meta_namespace_comes_from_setting_when_present(settings):
    settings.DJANGORDF_DEFAULT_NAMESPACE = "http://judaicalink.org/data/"
    from djangordf.models import RDFModel

    class Term(RDFModel):
        pass

    assert str(Term._meta.namespace) == "http://judaicalink.org/data/"


def test_meta_graph_iri_falls_back_to_sentinel(settings):
    if hasattr(settings, "DJANGORDF_DEFAULT_GRAPH"):
        del settings.DJANGORDF_DEFAULT_GRAPH
    from djangordf.models import RDFModel

    class Term(RDFModel):
        pass

    assert str(Term._meta.graph_iri) == "urn:djangordf:default"


def test_meta_class_iri_resolves_curie_strings():
    from djangordf.models import RDFModel

    class Term(RDFModel):
        class Meta:
            class_iri = "skos:Concept"

    assert Term._meta.class_iri == SKOS.Concept


def test_meta_explicit_namespace_and_graph_override_settings():
    from djangordf.models import RDFModel

    class Term(RDFModel):
        class Meta:
            namespace = "http://judaicalink.org/explicit/"
            graph_iri = "http://judaicalink.org/graph/explicit"

    assert str(Term._meta.namespace) == "http://judaicalink.org/explicit/"
    assert (
        str(Term._meta.graph_iri)
        == "http://judaicalink.org/graph/explicit"
    )


# -- model registry ---------------------------------------------------------


def test_subclasses_registered_under_their_name():
    from djangordf.models import RDFModel, get_registered_model

    class Term(RDFModel):
        pass

    assert get_registered_model("Term") is Term


# -- identity and DoesNotExist ----------------------------------------------


def test_instance_starts_without_iri():
    from djangordf.models import RDFModel

    class Term(RDFModel):
        pass

    assert Term().iri is None


def test_explicit_iri_is_kept_as_urirf():
    from djangordf.models import RDFModel

    class Term(RDFModel):
        pass

    inst = Term(iri="http://example.org/t1")
    assert isinstance(inst.iri, URIRef)
    assert str(inst.iri) == "http://example.org/t1"


def test_instances_compare_equal_by_iri():
    from djangordf.models import RDFModel

    class Term(RDFModel):
        pass

    a = Term(iri="http://example.org/x")
    b = Term(iri="http://example.org/x")
    c = Term(iri="http://example.org/y")
    assert a == b
    assert a != c


def test_instances_without_iri_only_equal_themselves():
    from djangordf.models import RDFModel

    class Term(RDFModel):
        pass

    a = Term()
    b = Term()
    assert a != b
    assert a == a


def test_each_subclass_has_its_own_does_not_exist():
    from djangordf.models import RDFModel

    class A(RDFModel):
        pass

    class B(RDFModel):
        pass

    assert A.DoesNotExist is not B.DoesNotExist
    assert issubclass(A.DoesNotExist, Exception)
    assert issubclass(B.DoesNotExist, Exception)


# -- save / delete round-trip via InMemoryBackend ---------------------------


def test_save_mints_iri_in_configured_namespace(settings):
    settings.DJANGORDF_DEFAULT_NAMESPACE = "http://judaicalink.org/data/"
    from djangordf.models import RDFModel

    class Term(RDFModel):
        title = Property(predicate=URIRef("http://example.org/title"))

    inst = Term()
    inst.title = "hello"
    inst.save()
    assert str(inst.iri).startswith("http://judaicalink.org/data/")


def test_save_writes_rdf_type_triple_into_configured_graph(settings):
    settings.DJANGORDF_DEFAULT_NAMESPACE = "http://example.org/d/"
    settings.DJANGORDF_DEFAULT_GRAPH = "http://example.org/g"
    settings.DJANGORDF_BACKEND = {
        "class": "djangordf.backends.memory.InMemoryBackend",
    }
    from djangordf.models import RDFModel
    from djangordf.conf import get_backend

    class Term(RDFModel):
        title = Property(predicate=URIRef("http://example.org/title"))

    inst = Term()
    inst.title = "hello"
    inst.save()

    # Read back via the backend the manager uses.
    backend = inst.objects.backend
    sparql = (
        "CONSTRUCT { ?s ?p ?o } WHERE { "
        f"GRAPH <{Term._meta.graph_iri}> {{ ?s ?p ?o }} "
        "}"
    )
    g = backend.query(sparql)
    from rdflib.namespace import RDF, SKOS
    assert (URIRef(inst.iri), RDF.type, SKOS.Concept) in g
```

- [ ] **Step 4.2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_models.py -v`
Expected: all fail with `ModuleNotFoundError: No module named 'djangordf.models'`.

- [ ] **Step 4.3: Implement RDFModel and the metaclass**

Create `djangordf/models.py`:

```python
"""RDFModel base class, metaclass, Meta resolution, model registry."""
import uuid
from dataclasses import dataclass

from django.conf import settings
from rdflib import URIRef
from rdflib.namespace import RDF

from .manager import RDFManager
from .properties import Property
from .skos import Concept as SKOS_CONCEPT, resolve_curie


_MODEL_REGISTRY: dict = {}


def get_registered_model(name: str):
    """Look up a model class by its name. Used for string targets in
    ``ObjectProperty("self", ...)`` and forward references; the full
    Property system in #7 reads through this."""
    return _MODEL_REGISTRY[name]


@dataclass
class _MetaInfo:
    class_iri: URIRef
    namespace: URIRef
    graph_iri: URIRef


def _build_meta(name: str, meta_cls) -> _MetaInfo:
    """Resolve the inner ``Meta`` of an RDFModel subclass into a frozen
    ``_MetaInfo`` instance, applying defaults from Django settings and
    CURIE resolution where appropriate."""
    raw_class_iri = getattr(meta_cls, "class_iri", None) if meta_cls else None
    if raw_class_iri is None:
        class_iri = SKOS_CONCEPT
    else:
        class_iri = resolve_curie(raw_class_iri)

    raw_namespace = getattr(meta_cls, "namespace", None) if meta_cls else None
    if raw_namespace is None:
        raw_namespace = getattr(settings, "DJANGORDF_DEFAULT_NAMESPACE", None)
    if raw_namespace is None:
        raw_namespace = f"urn:djangordf:{name.lower()}:"
    namespace = URIRef(raw_namespace)

    raw_graph = getattr(meta_cls, "graph_iri", None) if meta_cls else None
    if raw_graph is None:
        raw_graph = getattr(settings, "DJANGORDF_DEFAULT_GRAPH", None)
    if raw_graph is None:
        raw_graph = "urn:djangordf:default"
    graph_iri = URIRef(raw_graph)

    return _MetaInfo(
        class_iri=class_iri,
        namespace=namespace,
        graph_iri=graph_iri,
    )


class RDFModelMeta(type):
    def __new__(mcs, name, bases, namespace):
        properties = {}
        for attr, value in list(namespace.items()):
            if isinstance(value, Property):
                value.contribute_to_class(attr)
                properties[attr] = value

        cls = super().__new__(mcs, name, bases, namespace)
        cls._properties = properties

        meta_cls = namespace.get("Meta")
        cls._meta = _build_meta(name, meta_cls)

        if name != "RDFModel":
            cls.DoesNotExist = type(
                "DoesNotExist", (Exception,), {}
            )
            cls.objects = RDFManager(cls)
            _MODEL_REGISTRY[name] = cls

        return cls


class RDFModel(metaclass=RDFModelMeta):
    """Base class for triple-store-backed domain models."""

    def __init__(self, *, iri=None, **kwargs):
        self.iri = URIRef(iri) if iri is not None else None
        for attr, prop in self._properties.items():
            setattr(self, attr, kwargs.get(attr, prop.default()))

    # -- identity by IRI ----------------------------------------------------

    def __eq__(self, other):
        if not isinstance(other, RDFModel):
            return NotImplemented
        if self.iri is None or other.iri is None:
            return self is other
        return self.iri == other.iri

    def __hash__(self):
        if self.iri is None:
            return object.__hash__(self)
        return hash(self.iri)

    # -- serialisation ------------------------------------------------------

    def _to_triples(self):
        """Triples this instance should currently hold in the store.

        The full property->RDF mapping lands in #7. This milestone
        emits ``rdf:type`` plus any ``URIRef`` / ``Literal``-like
        attribute values whose Property declares an explicit predicate.
        """
        from rdflib import Literal

        triples = [(self.iri, RDF.type, self._meta.class_iri)]
        for attr, prop in self._properties.items():
            if prop.predicate is None:
                continue
            value = getattr(self, attr, None)
            if value is None:
                continue
            if isinstance(value, URIRef):
                obj = value
            elif isinstance(value, Literal):
                obj = value
            else:
                obj = Literal(value)
            triples.append((self.iri, prop.predicate, obj))
        return triples

    # -- persistence facade -------------------------------------------------

    def save(self):
        if self.iri is None:
            self.iri = URIRef(
                f"{self._meta.namespace}{uuid.uuid4().hex}"
            )
        self.objects.save(self)

    def delete(self):
        self.objects.delete(self)
```

- [ ] **Step 4.4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_models.py -v`
Expected: all tests pass.

- [ ] **Step 4.5: Run the full test suite to make sure nothing else broke**

Run: `.venv/bin/pytest -v`
Expected: every existing test still passes, every new test passes.

- [ ] **Step 4.6: Run flake8**

Run: `.venv/bin/flake8 djangordf tests setup.py`
Expected: clean.

- [ ] **Step 4.7: Commit**

```bash
git add djangordf/models.py tests/test_models.py
git commit -m "Add RDFModel base class and RDFModelMeta metaclass"
```

---

## Task 5: Re-export RDFModel and Property at the package top level

**Files:**
- Modify: `djangordf/__init__.py`

- [ ] **Step 5.1: Write the failing test**

Append to `tests/test_models.py`:

```python
def test_rdfmodel_is_importable_from_package_root():
    from djangordf import RDFModel as TopLevelModel
    from djangordf.models import RDFModel as ModuleModel
    assert TopLevelModel is ModuleModel


def test_property_is_importable_from_package_root():
    from djangordf import Property as TopLevelProperty
    from djangordf.properties import Property as ModuleProperty
    assert TopLevelProperty is ModuleProperty
```

- [ ] **Step 5.2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_models.py -v -k "importable_from_package_root"`
Expected: `ImportError: cannot import name 'RDFModel' from 'djangordf'` (or similar).

- [ ] **Step 5.3: Update djangordf/__init__.py**

Replace the contents of `djangordf/__init__.py` with:

```python
from .backends import InMemoryBackend, TripleStoreBackend
from .conf import get_backend
from .functions import export_model_to_rdf
from .models import RDFModel
from .properties import Property

__all__ = [
    "InMemoryBackend",
    "Property",
    "RDFModel",
    "TripleStoreBackend",
    "export_model_to_rdf",
    "get_backend",
]
```

- [ ] **Step 5.4: Run the tests to verify they pass**

Run: `.venv/bin/pytest -v`
Expected: all tests pass.

- [ ] **Step 5.5: Run flake8**

Run: `.venv/bin/flake8 djangordf tests setup.py`
Expected: clean.

- [ ] **Step 5.6: Commit**

```bash
git add djangordf/__init__.py tests/test_models.py
git commit -m "Re-export RDFModel and Property at the package top level"
```

---

## Task 6: Push the branch and open the pull request

**Files:** none, only git/gh operations.

- [ ] **Step 6.1: Push the branch**

Run: `git push -u origin feature/rdfmodel`
Expected: branch created on remote.

- [ ] **Step 6.2: Open the pull request closing issue #6**

Run:

```bash
gh pr create \
  --base development \
  --head feature/rdfmodel \
  --title "Add RDFModel base class and metaclass" \
  --body "$(cat <<'EOF'
## Summary

Lands the model layer's foundation: `RDFModel`, `RDFModelMeta`, `_build_meta`, per-subclass `DoesNotExist`, a process-wide model registry, and save/delete delegation through a minimal `RDFManager`. Third component of the §4 walking skeleton.

## Files

- `djangordf/models.py` — `RDFModelMeta`, `RDFModel`, `_build_meta`, registry
- `djangordf/properties.py` — minimal `Property` base (full type system lands in #7)
- `djangordf/skos.py` — `Concept` constant and a tiny CURIE resolver (full `NamespaceRegistry` lands in #9)
- `djangordf/manager.py` — minimal `RDFManager.save` / `RDFManager.delete` (full CRUD lands in #8)
- `djangordf/__init__.py` — re-export `RDFModel` and `Property`
- `tests/test_models.py`, `tests/test_properties.py`, `tests/test_skos.py`, `tests/test_manager.py`

## Test plan

- [x] `flake8 djangordf tests setup.py` clean
- [x] every existing test still green
- [x] new tests for metaclass collection, Meta defaults, CURIE class_iri, model registry, identity by IRI, per-subclass DoesNotExist, save/delete round-trip via InMemoryBackend
- [ ] CI green on Python 3.10, 3.11, 3.12

## Notes

`properties.py`, `skos.py` and `manager.py` ship intentionally minimal stubs so this PR is self-contained. Their full implementations are scoped to:

- #7 — full Property type system (DataProperty, LangStringProperty, ObjectProperty, URIProperty)
- #8 — full `RDFManager` / `RDFQuerySet` CRUD
- #9 — `NamespaceRegistry` and the SKOS predicate-default convention map

## Reference

Design spec [§5](docs/superpowers/specs/2026-05-22-rdfmodel-walking-skeleton-design.md).

Closes #6.
EOF
)"
```

- [ ] **Step 6.3: Wait for CI**

Run in the background:

```bash
until [ "$(gh pr view --json statusCheckRollup --jq '[.statusCheckRollup[]] | length')" -gt 0 ] && \
      [ "$(gh pr view --json statusCheckRollup --jq '[.statusCheckRollup[] | select(.status != "COMPLETED")] | length')" -eq 0 ]; do
    sleep 15
done
gh pr view --json statusCheckRollup --jq '[.statusCheckRollup[] | {name, conclusion}]'
```

Expected: all three matrix entries (`test (3.10)`, `test (3.11)`, `test (3.12)`) show `SUCCESS`.

- [ ] **Step 6.4: Stop**

Hand back to the user for review and merge. Do not merge yourself.

---

## Self-review notes

- Spec §5 `RDFModelMeta` collects Property descriptors — Task 4.
- Spec §5 `RDFModel.__init__(*, iri=None, **kwargs)` — Task 4.
- Spec §5 `RDFModel.save()` / `delete()` — Task 4 (facade) + Task 3 (SPARQL).
- Spec §5 `__eq__` / `__hash__` by IRI — Task 4.
- Spec §5 `_build_meta(cls, meta)` with CURIE resolution and defaults — Task 4 (resolution) + Task 2 (CURIE helper).
- Spec §5 process-wide model registry — Task 4 (`_MODEL_REGISTRY` + `get_registered_model`).
- Spec §5 per-subclass `DoesNotExist` — Task 4.
- Spec §5 `Meta.abstract`, `subClassOf`, signals, reverse accessors — explicitly out of scope, no tasks.
- All file names, function names, attribute names match between tasks (`Property.contribute_to_class`, `Property.attr_name`, `RDFManager._backend`, `_MODEL_REGISTRY`, `_build_meta`, `_to_triples`).
- All commit messages, code comments, PR body and issue body are English.
- Branch name `feature/rdfmodel` follows the project's convention.
- No placeholders or "TBD".
