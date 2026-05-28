# Property Type System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the minimal `Property` stub from issue #6 with the full property type system: `DataProperty`, `LangStringProperty`, `ObjectProperty`, `URIProperty`, a `LangString` dataclass, and per-property cardinality (`many=False/True`). Refactor `RDFModel._to_triples` to delegate value serialisation to each property's `to_rdf(subject, value)`. Close GitHub issue #7.

**Architecture:** `Property` becomes a small base class with `to_rdf(subject, value)` and `from_rdf(graph, subject)` extension points. Each concrete subclass implements both, owns its `many=False/True` semantics, and produces `rdflib.Literal`/`rdflib.URIRef` terms. `LangString` is a frozen dataclass that pairs a string value with a language tag. `ObjectProperty` accepts a string target (`"self"` or a model class name) and resolves it lazily through the process-wide model registry from issue #6 the first time it is asked for triples. Implicit SKOS predicate assignment (when `predicate=None`) is intentionally **out of scope** here — it lands in #9 once the full `NamespaceRegistry` exists.

**Tech Stack:** Python 3.10+, rdflib 7.x, Django 3.2+, pytest 9.x, pytest-django 4.x.

**Spec reference:** [docs/superpowers/specs/2026-05-22-rdfmodel-walking-skeleton-design.md](../specs/2026-05-22-rdfmodel-walking-skeleton-design.md) §6.

**Issue:** [#7 Property type system](https://github.com/judaicalink/djangordf/issues/7).

---

## File structure

| File | Responsibility | Action |
|---|---|---|
| `djangordf/namespaces.py` | `LangString` dataclass (full `NamespaceRegistry` lands in #9). | create |
| `djangordf/properties.py` | `Property` base + `DataProperty`, `LangStringProperty`, `ObjectProperty`, `URIProperty`. | rewrite |
| `djangordf/models.py` | `RDFModelMeta` injects the owner class via `contribute_to_class`; `RDFModel._to_triples` now delegates to `prop.to_rdf`. | modify |
| `djangordf/__init__.py` | Re-export the new property types and `LangString`. | modify |
| `tests/test_namespaces.py` | Tests for `LangString` value semantics. | create |
| `tests/test_properties.py` | Tests for each property type's `to_rdf`/`from_rdf`, both scalar and `many=True`. | extend |
| `tests/test_models.py` | Add one regression test that proves the new `_to_triples` path delegates to `prop.to_rdf`. | extend |

---

## Task 1: LangString dataclass

**Files:**
- Create: `djangordf/namespaces.py`
- Create: `tests/test_namespaces.py`

- [ ] **Step 1.1: Write the failing test**

Create `tests/test_namespaces.py`:

```python
"""Tests for djangordf.namespaces (LangString in this milestone)."""


def test_langstring_holds_value_and_lang():
    from djangordf.namespaces import LangString
    ls = LangString("Buch", "de")
    assert ls.value == "Buch"
    assert ls.lang == "de"


def test_langstring_is_frozen():
    import dataclasses
    from djangordf.namespaces import LangString
    ls = LangString("Buch", "de")
    try:
        ls.value = "Roman"
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("LangString must be frozen")


def test_langstring_equality_by_value_and_lang():
    from djangordf.namespaces import LangString
    assert LangString("Buch", "de") == LangString("Buch", "de")
    assert LangString("Buch", "de") != LangString("Buch", "en")
    assert LangString("Buch", "de") != LangString("Roman", "de")


def test_langstring_is_hashable():
    from djangordf.namespaces import LangString
    s = {LangString("Buch", "de"), LangString("Buch", "de")}
    assert len(s) == 1
```

- [ ] **Step 1.2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_namespaces.py -v`
Expected: 4 failures with `ModuleNotFoundError: No module named 'djangordf.namespaces'`.

- [ ] **Step 1.3: Implement LangString**

Create `djangordf/namespaces.py`:

```python
"""Namespace utilities for djangordf.

This milestone ships only ``LangString``. The full ``NamespaceRegistry``
with CURIE resolution and prefix bindings lands in issue #9.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class LangString:
    """A language-tagged literal, paired with a BCP 47 language tag.

    Used by ``LangStringProperty`` to round-trip ``rdf:langString``
    values cleanly between Python and the triple store.
    """

    value: str
    lang: str
```

- [ ] **Step 1.4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_namespaces.py -v`
Expected: 4 passed.

- [ ] **Step 1.5: Run flake8**

Run: `.venv/bin/flake8 djangordf tests`
Expected: clean.

- [ ] **Step 1.6: Commit**

```bash
git add djangordf/namespaces.py tests/test_namespaces.py
git commit -m "Add LangString dataclass for language-tagged literals"
```

---

## Task 2: Property base — to_rdf / from_rdf extension points

**Files:**
- Modify: `djangordf/properties.py`
- Modify: `tests/test_properties.py`

- [ ] **Step 2.1: Append the failing tests**

Append to `tests/test_properties.py`:

```python
def test_property_to_rdf_emits_no_triples_for_none_value():
    from rdflib import URIRef
    from djangordf.properties import Property
    p = Property(predicate=URIRef("http://example.org/p"))
    triples = p.to_rdf(URIRef("http://example.org/s"), None)
    assert triples == []


def test_property_from_rdf_returns_none_when_no_match():
    from rdflib import Graph, URIRef
    from djangordf.properties import Property
    p = Property(predicate=URIRef("http://example.org/p"))
    assert p.from_rdf(Graph(), URIRef("http://example.org/s")) is None


def test_property_contribute_to_class_accepts_owner_class():
    from djangordf.properties import Property
    p = Property()
    p.contribute_to_class("title", owner_class=object)
    assert p.attr_name == "title"
    assert p.owner_class is object
```

- [ ] **Step 2.2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_properties.py -v`
Expected: the three new tests fail with `AttributeError` (`Property` has no `to_rdf`/`from_rdf`, `contribute_to_class` does not accept `owner_class`).

- [ ] **Step 2.3: Extend the Property base**

Replace `djangordf/properties.py` with:

```python
"""Declarative property descriptors for RDFModel.

Property type system (issue #7). The metaclass collects ``Property``
instances at class creation, hands each one the owner class via
``contribute_to_class``, and later delegates RDF serialisation /
deserialisation to ``to_rdf`` / ``from_rdf`` per property.
"""
from typing import Optional

from rdflib import URIRef


class Property:
    """Base class for declarative property descriptors.

    Subclasses override ``to_rdf`` and ``from_rdf`` to map Python values
    to RDF terms and back. The base implementation is a no-op so simple
    direct uses of ``Property`` keep working — useful for tests that
    only need a predicate stub.
    """

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
        self.owner_class = None

    def contribute_to_class(self, attr_name: str, owner_class=None) -> None:
        self.attr_name = attr_name
        if owner_class is not None:
            self.owner_class = owner_class

    def default(self):
        if self.many:
            return []
        return self._default

    # -- RDF serialisation extension points ---------------------------------

    def to_rdf(self, subject, value):
        """Return the triples this property contributes for ``value``.

        Default implementation: emit no triples. Concrete subclasses
        override.
        """
        return []

    def from_rdf(self, graph, subject):
        """Read this property's value back out of a graph.

        Default implementation returns ``None`` (scalar) or ``[]`` (many).
        """
        return [] if self.many else None
```

- [ ] **Step 2.4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_properties.py -v`
Expected: all tests pass (3 pre-existing from #6 + 3 new = 6).

- [ ] **Step 2.5: Run flake8**

Run: `.venv/bin/flake8 djangordf tests`
Expected: clean.

- [ ] **Step 2.6: Commit**

```bash
git add djangordf/properties.py tests/test_properties.py
git commit -m "Extend Property base with to_rdf, from_rdf and owner_class"
```

---

## Task 3: DataProperty

**Files:**
- Modify: `djangordf/properties.py`
- Modify: `tests/test_properties.py`

- [ ] **Step 3.1: Append the failing tests**

Append to `tests/test_properties.py`:

```python
def test_data_property_scalar_to_rdf_emits_typed_literal():
    from rdflib import Literal, URIRef
    from rdflib.namespace import XSD
    from djangordf.properties import DataProperty

    prop = DataProperty(
        predicate=URIRef("http://example.org/count"),
        datatype=XSD.integer,
    )
    triples = prop.to_rdf(URIRef("http://example.org/s"), 42)
    assert triples == [
        (
            URIRef("http://example.org/s"),
            URIRef("http://example.org/count"),
            Literal(42, datatype=XSD.integer),
        )
    ]


def test_data_property_scalar_to_rdf_skips_none():
    from rdflib import URIRef
    from rdflib.namespace import XSD
    from djangordf.properties import DataProperty

    prop = DataProperty(
        predicate=URIRef("http://example.org/count"),
        datatype=XSD.integer,
    )
    assert prop.to_rdf(URIRef("http://example.org/s"), None) == []


def test_data_property_many_to_rdf_emits_one_triple_per_value():
    from rdflib import Literal, URIRef
    from rdflib.namespace import XSD
    from djangordf.properties import DataProperty

    prop = DataProperty(
        predicate=URIRef("http://example.org/n"),
        datatype=XSD.integer,
        many=True,
    )
    triples = prop.to_rdf(URIRef("http://example.org/s"), [1, 2, 3])
    assert len(triples) == 3
    objects = sorted(int(t[2]) for t in triples)
    assert objects == [1, 2, 3]


def test_data_property_scalar_from_rdf_returns_python_value():
    from rdflib import Graph, Literal, URIRef
    from rdflib.namespace import XSD
    from djangordf.properties import DataProperty

    g = Graph()
    s = URIRef("http://example.org/s")
    p = URIRef("http://example.org/count")
    g.add((s, p, Literal(42, datatype=XSD.integer)))

    prop = DataProperty(predicate=p, datatype=XSD.integer)
    assert prop.from_rdf(g, s) == 42


def test_data_property_many_from_rdf_returns_list_of_values():
    from rdflib import Graph, Literal, URIRef
    from rdflib.namespace import XSD
    from djangordf.properties import DataProperty

    g = Graph()
    s = URIRef("http://example.org/s")
    p = URIRef("http://example.org/n")
    for v in (1, 2, 3):
        g.add((s, p, Literal(v, datatype=XSD.integer)))

    prop = DataProperty(predicate=p, datatype=XSD.integer, many=True)
    assert sorted(prop.from_rdf(g, s)) == [1, 2, 3]


def test_data_property_scalar_from_rdf_returns_none_when_missing():
    from rdflib import Graph, URIRef
    from rdflib.namespace import XSD
    from djangordf.properties import DataProperty

    prop = DataProperty(
        predicate=URIRef("http://example.org/p"),
        datatype=XSD.integer,
    )
    assert prop.from_rdf(Graph(), URIRef("http://example.org/s")) is None
```

- [ ] **Step 3.2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_properties.py -v`
Expected: six new failures (`ImportError: cannot import name 'DataProperty'`).

- [ ] **Step 3.3: Implement DataProperty**

Append to `djangordf/properties.py`:

```python
from rdflib import Literal


class DataProperty(Property):
    """Typed-literal data property (xsd:string, xsd:integer, ...)."""

    def __init__(
        self,
        predicate: Optional[URIRef] = None,
        *,
        datatype: Optional[URIRef] = None,
        many: bool = False,
        required: bool = False,
        default=None,
    ) -> None:
        super().__init__(
            predicate,
            many=many,
            required=required,
            default=default,
        )
        self.datatype = (
            URIRef(datatype) if datatype is not None else None
        )

    def to_rdf(self, subject, value):
        if value is None:
            return []
        if self.many:
            return [
                (subject, self.predicate, Literal(v, datatype=self.datatype))
                for v in value
            ]
        return [
            (subject, self.predicate, Literal(value, datatype=self.datatype))
        ]

    def from_rdf(self, graph, subject):
        objects = list(graph.objects(subject, self.predicate))
        if self.many:
            return [self._coerce(o) for o in objects]
        if not objects:
            return None
        return self._coerce(objects[0])

    @staticmethod
    def _coerce(literal):
        try:
            return literal.toPython()
        except Exception:
            return str(literal)
```

- [ ] **Step 3.4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_properties.py -v`
Expected: 12 passed (6 pre-existing + 6 new).

- [ ] **Step 3.5: Run flake8**

Run: `.venv/bin/flake8 djangordf tests`
Expected: clean.

- [ ] **Step 3.6: Commit**

```bash
git add djangordf/properties.py tests/test_properties.py
git commit -m "Add DataProperty for typed literals"
```

---

## Task 4: LangStringProperty

**Files:**
- Modify: `djangordf/properties.py`
- Modify: `tests/test_properties.py`

- [ ] **Step 4.1: Append the failing tests**

Append to `tests/test_properties.py`:

```python
def test_lang_string_property_scalar_to_rdf():
    from rdflib import Literal, URIRef
    from djangordf.namespaces import LangString
    from djangordf.properties import LangStringProperty

    prop = LangStringProperty(
        predicate=URIRef("http://example.org/label")
    )
    triples = prop.to_rdf(
        URIRef("http://example.org/s"),
        LangString("Buch", "de"),
    )
    assert triples == [
        (
            URIRef("http://example.org/s"),
            URIRef("http://example.org/label"),
            Literal("Buch", lang="de"),
        )
    ]


def test_lang_string_property_many_to_rdf():
    from rdflib import URIRef
    from djangordf.namespaces import LangString
    from djangordf.properties import LangStringProperty

    prop = LangStringProperty(
        predicate=URIRef("http://example.org/label"),
        many=True,
    )
    triples = prop.to_rdf(
        URIRef("http://example.org/s"),
        [LangString("Buch", "de"), LangString("Book", "en")],
    )
    assert len(triples) == 2
    langs = sorted(t[2].language for t in triples)
    assert langs == ["de", "en"]


def test_lang_string_property_from_rdf_round_trip():
    from rdflib import Graph, Literal, URIRef
    from djangordf.namespaces import LangString
    from djangordf.properties import LangStringProperty

    g = Graph()
    s = URIRef("http://example.org/s")
    p = URIRef("http://example.org/label")
    g.add((s, p, Literal("Buch", lang="de")))
    g.add((s, p, Literal("Book", lang="en")))

    prop = LangStringProperty(predicate=p, many=True)
    result = prop.from_rdf(g, s)
    assert set(result) == {
        LangString("Buch", "de"),
        LangString("Book", "en"),
    }


def test_lang_string_property_scalar_from_rdf_missing_returns_none():
    from rdflib import Graph, URIRef
    from djangordf.properties import LangStringProperty

    prop = LangStringProperty(
        predicate=URIRef("http://example.org/label")
    )
    assert prop.from_rdf(Graph(), URIRef("http://example.org/s")) is None
```

- [ ] **Step 4.2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_properties.py -v`
Expected: four new failures with `ImportError`.

- [ ] **Step 4.3: Implement LangStringProperty**

Append to `djangordf/properties.py`:

```python
from .namespaces import LangString


class LangStringProperty(Property):
    """Language-tagged string property mapping to ``rdf:langString``."""

    def to_rdf(self, subject, value):
        if value is None:
            return []
        if self.many:
            return [
                (subject, self.predicate, Literal(ls.value, lang=ls.lang))
                for ls in value
            ]
        return [
            (subject, self.predicate, Literal(value.value, lang=value.lang))
        ]

    def from_rdf(self, graph, subject):
        objects = list(graph.objects(subject, self.predicate))
        results = [
            LangString(str(o), o.language)
            for o in objects
            if getattr(o, "language", None) is not None
        ]
        if self.many:
            return results
        return results[0] if results else None
```

- [ ] **Step 4.4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_properties.py -v`
Expected: 16 passed.

- [ ] **Step 4.5: Run flake8**

Run: `.venv/bin/flake8 djangordf tests`
Expected: clean.

- [ ] **Step 4.6: Commit**

```bash
git add djangordf/properties.py tests/test_properties.py
git commit -m "Add LangStringProperty for rdf:langString values"
```

---

## Task 5: URIProperty

**Files:**
- Modify: `djangordf/properties.py`
- Modify: `tests/test_properties.py`

- [ ] **Step 5.1: Append the failing tests**

Append to `tests/test_properties.py`:

```python
def test_uri_property_scalar_to_rdf_accepts_string_or_uriref():
    from rdflib import URIRef
    from djangordf.properties import URIProperty

    prop = URIProperty(
        predicate=URIRef("http://example.org/exactMatch")
    )

    from_str = prop.to_rdf(
        URIRef("http://example.org/s"),
        "http://example.org/o",
    )
    from_uri = prop.to_rdf(
        URIRef("http://example.org/s"),
        URIRef("http://example.org/o"),
    )
    assert from_str == from_uri
    assert from_str[0][2] == URIRef("http://example.org/o")


def test_uri_property_many_to_rdf():
    from rdflib import URIRef
    from djangordf.properties import URIProperty

    prop = URIProperty(
        predicate=URIRef("http://example.org/seeAlso"),
        many=True,
    )
    triples = prop.to_rdf(
        URIRef("http://example.org/s"),
        [
            "http://example.org/a",
            URIRef("http://example.org/b"),
        ],
    )
    assert len(triples) == 2
    targets = {t[2] for t in triples}
    assert URIRef("http://example.org/a") in targets
    assert URIRef("http://example.org/b") in targets


def test_uri_property_from_rdf_returns_uriref():
    from rdflib import Graph, URIRef
    from djangordf.properties import URIProperty

    g = Graph()
    s = URIRef("http://example.org/s")
    p = URIRef("http://example.org/exactMatch")
    g.add((s, p, URIRef("http://example.org/o")))

    prop = URIProperty(predicate=p)
    result = prop.from_rdf(g, s)
    assert isinstance(result, URIRef)
    assert str(result) == "http://example.org/o"
```

- [ ] **Step 5.2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_properties.py -v`
Expected: three new failures with `ImportError`.

- [ ] **Step 5.3: Implement URIProperty**

Append to `djangordf/properties.py`:

```python
class URIProperty(Property):
    """Raw-IRI property (no Python wrapper, just ``URIRef``)."""

    def to_rdf(self, subject, value):
        if value is None:
            return []
        if self.many:
            return [
                (subject, self.predicate, URIRef(v))
                for v in value
            ]
        return [(subject, self.predicate, URIRef(value))]

    def from_rdf(self, graph, subject):
        objects = list(graph.objects(subject, self.predicate))
        if self.many:
            return [URIRef(o) for o in objects]
        return URIRef(objects[0]) if objects else None
```

- [ ] **Step 5.4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_properties.py -v`
Expected: 19 passed.

- [ ] **Step 5.5: Run flake8**

Run: `.venv/bin/flake8 djangordf tests`
Expected: clean.

- [ ] **Step 5.6: Commit**

```bash
git add djangordf/properties.py tests/test_properties.py
git commit -m "Add URIProperty for raw-IRI values"
```

---

## Task 6: ObjectProperty with lazy target resolution

**Files:**
- Modify: `djangordf/properties.py`
- Modify: `tests/test_properties.py`

- [ ] **Step 6.1: Append the failing tests**

Append to `tests/test_properties.py`:

```python
def test_object_property_to_rdf_takes_rdf_model_instance():
    from rdflib import URIRef
    from djangordf.models import RDFModel
    from djangordf.properties import ObjectProperty

    class TargetA(RDFModel):
        pass

    target = TargetA(iri="http://example.org/target/1")
    prop = ObjectProperty(
        TargetA,
        predicate=URIRef("http://example.org/related"),
    )
    triples = prop.to_rdf(
        URIRef("http://example.org/s"), target,
    )
    assert triples == [
        (
            URIRef("http://example.org/s"),
            URIRef("http://example.org/related"),
            URIRef("http://example.org/target/1"),
        )
    ]


def test_object_property_to_rdf_accepts_uriref_too():
    from rdflib import URIRef
    from djangordf.models import RDFModel
    from djangordf.properties import ObjectProperty

    class TargetB(RDFModel):
        pass

    prop = ObjectProperty(
        TargetB,
        predicate=URIRef("http://example.org/related"),
    )
    triples = prop.to_rdf(
        URIRef("http://example.org/s"),
        URIRef("http://example.org/target/2"),
    )
    assert triples[0][2] == URIRef("http://example.org/target/2")


def test_object_property_many_to_rdf():
    from rdflib import URIRef
    from djangordf.models import RDFModel
    from djangordf.properties import ObjectProperty

    class TargetC(RDFModel):
        pass

    a = TargetC(iri="http://example.org/c/a")
    b = TargetC(iri="http://example.org/c/b")
    prop = ObjectProperty(
        TargetC,
        predicate=URIRef("http://example.org/related"),
        many=True,
    )
    triples = prop.to_rdf(URIRef("http://example.org/s"), [a, b])
    targets = {t[2] for t in triples}
    assert targets == {
        URIRef("http://example.org/c/a"),
        URIRef("http://example.org/c/b"),
    }


def test_object_property_from_rdf_returns_iris():
    """In the walking-skeleton milestone the read side returns IRIs;
    full instance hydration is the manager's job (issue #8)."""
    from rdflib import Graph, URIRef
    from djangordf.models import RDFModel
    from djangordf.properties import ObjectProperty

    class TargetD(RDFModel):
        pass

    g = Graph()
    s = URIRef("http://example.org/s")
    p = URIRef("http://example.org/related")
    g.add((s, p, URIRef("http://example.org/d/1")))

    prop = ObjectProperty(TargetD, predicate=p)
    assert prop.from_rdf(g, s) == URIRef("http://example.org/d/1")


def test_object_property_self_target_resolves_to_owner_class():
    from djangordf.models import RDFModel
    from djangordf.properties import ObjectProperty

    class TermSelf(RDFModel):
        broader = ObjectProperty("self")

    prop = TermSelf._properties["broader"]
    assert prop.target_class is TermSelf


def test_object_property_string_target_resolves_through_registry():
    from djangordf.models import RDFModel
    from djangordf.properties import ObjectProperty

    class TargetByName(RDFModel):
        pass

    class Referrer(RDFModel):
        link = ObjectProperty("TargetByName")

    prop = Referrer._properties["link"]
    assert prop.target_class is TargetByName
```

- [ ] **Step 6.2: Run the tests to verify they fail**

Run: `.venv/bin/pytest tests/test_properties.py -v`
Expected: six new failures (`ImportError: cannot import name 'ObjectProperty'`).

- [ ] **Step 6.3: Implement ObjectProperty**

Append to `djangordf/properties.py`:

```python
class ObjectProperty(Property):
    """Link between two RDFModel instances.

    ``target`` may be the target class, the string ``"self"``, or the
    name of a registered model class — the last two resolve lazily
    through ``djangordf.models.get_registered_model`` the first time
    ``target_class`` is accessed.
    """

    def __init__(
        self,
        target,
        predicate: Optional[URIRef] = None,
        *,
        many: bool = False,
        required: bool = False,
        default=None,
    ) -> None:
        super().__init__(
            predicate,
            many=many,
            required=required,
            default=default,
        )
        self._target = target

    @property
    def target_class(self):
        if isinstance(self._target, type):
            return self._target
        if self._target == "self":
            return self.owner_class
        from .models import get_registered_model
        return get_registered_model(self._target)

    def to_rdf(self, subject, value):
        if value is None:
            return []
        if self.many:
            return [
                (subject, self.predicate, self._iri_of(v))
                for v in value
            ]
        return [(subject, self.predicate, self._iri_of(value))]

    def from_rdf(self, graph, subject):
        objects = list(graph.objects(subject, self.predicate))
        if self.many:
            return [URIRef(o) for o in objects]
        return URIRef(objects[0]) if objects else None

    @staticmethod
    def _iri_of(value):
        if isinstance(value, URIRef):
            return value
        return URIRef(value.iri)
```

- [ ] **Step 6.4: Run the tests to verify they fail with `owner_class` not being set yet**

Run: `.venv/bin/pytest tests/test_properties.py::test_object_property_self_target_resolves_to_owner_class -v`
Expected: failure — `owner_class` is still `None` because the metaclass does not yet pass it to `contribute_to_class`. This is fixed in Task 7.

- [ ] **Step 6.5: Commit**

```bash
git add djangordf/properties.py tests/test_properties.py
git commit -m "Add ObjectProperty with lazy target resolution"
```

---

## Task 7: Metaclass wiring + RDFModel.\_to\_triples refactor

**Files:**
- Modify: `djangordf/models.py`
- Modify: `tests/test_models.py`

- [ ] **Step 7.1: Append the failing regression test**

Append to `tests/test_models.py`:

```python
def test_to_triples_delegates_to_property_to_rdf(settings):
    """The RDFModel._to_triples path must dispatch through each
    property's ``to_rdf`` (proven by checking xsd:integer typing, which
    the inline path from #6 did not emit)."""
    settings.DJANGORDF_DEFAULT_NAMESPACE = "http://example.org/td/"
    from rdflib import Literal, URIRef
    from rdflib.namespace import XSD

    from djangordf.models import RDFModel
    from djangordf.properties import DataProperty

    class CountedTerm(RDFModel):
        count = DataProperty(
            predicate=URIRef("http://example.org/n"),
            datatype=XSD.integer,
        )

    inst = CountedTerm(iri="http://example.org/td/x")
    inst.count = 42
    triples = inst._to_triples()
    assert (
        URIRef("http://example.org/td/x"),
        URIRef("http://example.org/n"),
        Literal(42, datatype=XSD.integer),
    ) in triples
```

- [ ] **Step 7.2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_models.py::test_to_triples_delegates_to_property_to_rdf -v`
Expected: failure — the current `_to_triples` emits `Literal(42)` without `datatype=XSD.integer`.

- [ ] **Step 7.3: Update the metaclass to pass the owner class and rewrite _to_triples**

Replace `djangordf/models.py` with the following (the changes vs. the file from #6 are: metaclass now calls `contribute_to_class(attr, owner_class=cls)` after the class is built, and `_to_triples` delegates to `prop.to_rdf`):

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
    ``ObjectProperty("self", ...)`` and forward references."""
    return _MODEL_REGISTRY[name]


@dataclass
class _MetaInfo:
    class_iri: URIRef
    namespace: URIRef
    graph_iri: URIRef


def _build_meta(name: str, meta_cls) -> _MetaInfo:
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
                properties[attr] = value

        cls = super().__new__(mcs, name, bases, namespace)
        cls._properties = properties

        # Now that ``cls`` exists, hand each property the owner class so
        # ObjectProperty("self") can resolve.
        for attr, prop in properties.items():
            prop.contribute_to_class(attr, owner_class=cls)

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

    def _to_triples(self):
        """Emit all triples this instance currently represents.

        Delegates to each property's ``to_rdf`` so concrete property
        types (DataProperty / LangStringProperty / ObjectProperty /
        URIProperty) own their own serialisation rules.
        """
        triples = [(self.iri, RDF.type, self._meta.class_iri)]
        for attr, prop in self._properties.items():
            if prop.predicate is None:
                continue
            value = getattr(self, attr, None)
            triples.extend(prop.to_rdf(self.iri, value))
        return triples

    def save(self):
        if self.iri is None:
            self.iri = URIRef(
                f"{self._meta.namespace}{uuid.uuid4().hex}"
            )
        self.objects.save(self)

    def delete(self):
        self.objects.delete(self)
```

- [ ] **Step 7.4: Run the affected suites to verify everything passes**

Run: `.venv/bin/pytest tests/test_properties.py tests/test_models.py -v`
Expected: every test (including the previously red `test_object_property_self_target_resolves_to_owner_class` and `test_to_triples_delegates_to_property_to_rdf`) passes.

- [ ] **Step 7.5: Run the full suite**

Run: `.venv/bin/pytest -v`
Expected: every test green; pre-existing tests from #4/#5/#6 still pass.

- [ ] **Step 7.6: Run flake8**

Run: `.venv/bin/flake8 djangordf tests setup.py`
Expected: clean.

- [ ] **Step 7.7: Commit**

```bash
git add djangordf/models.py tests/test_models.py
git commit -m "Delegate RDFModel._to_triples to per-property to_rdf"
```

---

## Task 8: Re-exports, push and pull request

**Files:**
- Modify: `djangordf/__init__.py`
- Modify: `tests/test_models.py`

- [ ] **Step 8.1: Write the failing import tests**

Append to `tests/test_models.py`:

```python
def test_new_property_types_are_importable_from_package_root():
    from djangordf import (
        DataProperty as TopData,
        LangStringProperty as TopLang,
        ObjectProperty as TopObj,
        URIProperty as TopURI,
        LangString as TopLangString,
    )
    from djangordf.properties import (
        DataProperty, LangStringProperty, ObjectProperty, URIProperty,
    )
    from djangordf.namespaces import LangString
    assert TopData is DataProperty
    assert TopLang is LangStringProperty
    assert TopObj is ObjectProperty
    assert TopURI is URIProperty
    assert TopLangString is LangString
```

- [ ] **Step 8.2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_models.py::test_new_property_types_are_importable_from_package_root -v`
Expected: failure with `ImportError`.

- [ ] **Step 8.3: Update djangordf/__init__.py**

Replace `djangordf/__init__.py` with:

```python
from .backends import FusekiBackend, InMemoryBackend, TripleStoreBackend
from .conf import get_backend
from .functions import export_model_to_rdf
from .models import RDFModel
from .namespaces import LangString
from .properties import (
    DataProperty,
    LangStringProperty,
    ObjectProperty,
    Property,
    URIProperty,
)

__all__ = [
    "DataProperty",
    "FusekiBackend",
    "InMemoryBackend",
    "LangString",
    "LangStringProperty",
    "ObjectProperty",
    "Property",
    "RDFModel",
    "TripleStoreBackend",
    "URIProperty",
    "export_model_to_rdf",
    "get_backend",
]
```

- [ ] **Step 8.4: Run the full suite**

Run: `.venv/bin/pytest -v`
Expected: every test green.

- [ ] **Step 8.5: Run flake8**

Run: `.venv/bin/flake8 djangordf tests setup.py`
Expected: clean.

- [ ] **Step 8.6: Commit**

```bash
git add djangordf/__init__.py tests/test_models.py
git commit -m "Re-export new property types and LangString at package root"
```

- [ ] **Step 8.7: Push the branch**

Run: `git push -u origin feature/property-types`
Expected: branch created on remote.

- [ ] **Step 8.8: Open the pull request**

Run:

```bash
gh pr create \
  --base development \
  --head feature/property-types \
  --title "Add property type system: DataProperty, LangStringProperty, ObjectProperty, URIProperty" \
  --body "$(cat <<'EOF'
## Summary

Replaces the minimal ``Property`` stub from #6 with the full property type system:

- ``DataProperty`` for typed literals (xsd:string, xsd:integer, xsd:dateTime, ...)
- ``LangStringProperty`` for ``rdf:langString`` values via a ``LangString(value, lang)`` dataclass
- ``ObjectProperty`` for instance-to-instance links, with lazy ``"self"`` / string-name target resolution through the model registry from #6
- ``URIProperty`` for raw IRI values

Each property type implements ``to_rdf(subject, value)`` and ``from_rdf(graph, subject)`` and honours ``many=False/True``. ``RDFModel._to_triples`` now delegates to ``prop.to_rdf`` instead of doing the inline ``URIRef``/``Literal`` dance, so concrete property types own their own RDF mapping.

## Files

- ``djangordf/namespaces.py`` — ``LangString`` dataclass (full ``NamespaceRegistry`` lands in #9)
- ``djangordf/properties.py`` — base ``Property`` + four concrete types
- ``djangordf/models.py`` — metaclass now injects ``owner_class`` via ``contribute_to_class``; ``_to_triples`` delegates
- ``djangordf/__init__.py`` — re-exports
- ``tests/test_namespaces.py``, ``tests/test_properties.py``, ``tests/test_models.py``

## Test plan

- [x] ``flake8 djangordf tests setup.py`` clean
- [x] full pytest suite green locally
- [ ] CI green on Python 3.10, 3.11, 3.12

## Notes

Implicit SKOS predicate assignment (``pref_label`` -> ``skos:prefLabel`` when ``predicate=None``) is intentionally **not** here — it depends on the full ``NamespaceRegistry`` + ``DEFAULT_PREDICATES`` map landing in #9. Until then a ``Property`` with no explicit predicate emits nothing, which keeps behaviour predictable.

## Reference

Design spec [§6](docs/superpowers/specs/2026-05-22-rdfmodel-walking-skeleton-design.md).

Closes #7.
EOF
)"
```

- [ ] **Step 8.9: Wait for CI**

Run in the background:

```bash
until [ "$(gh pr view --json statusCheckRollup --jq '[.statusCheckRollup[]] | length')" -gt 0 ] && \
      [ "$(gh pr view --json statusCheckRollup --jq '[.statusCheckRollup[] | select(.status != "COMPLETED")] | length')" -eq 0 ]; do
    sleep 15
done
gh pr view --json statusCheckRollup --jq '[.statusCheckRollup[] | {name, conclusion}]'
```

Expected: all three matrix entries SUCCESS.

- [ ] **Step 8.10: Stop**

Hand back to the user for review and merge.

---

## Self-review notes

- Spec §6 ``DataProperty`` — Task 3.
- Spec §6 ``LangStringProperty`` + ``LangString`` dataclass — Tasks 1 + 4.
- Spec §6 ``ObjectProperty`` + ``"self"`` / forward reference resolution — Task 6 + Task 7 (metaclass wiring).
- Spec §6 ``URIProperty`` — Task 5.
- Spec §6 cardinality ``many=False/True`` — covered inside every property task.
- Spec §6 implicit SKOS predicate assignment in the metaclass — explicitly **deferred to #9**, called out in the PR body so reviewers know it's intentional.
- Spec §6 ``RDFModel._to_triples`` delegates through ``prop.to_rdf`` — Task 7.
- Spec §6 out-of-scope (validator chains, ``choices``, FK cascade, reverse accessors) — no tasks.
- All names align: ``Property.to_rdf``, ``Property.from_rdf``, ``Property.contribute_to_class(attr, owner_class=...)``, ``ObjectProperty.target_class``, ``LangString(value, lang)``.
- All commit messages, code comments, PR body and issue body are English.
- Branch name ``feature/property-types`` follows the project's convention.
- No placeholders or "TBD".
