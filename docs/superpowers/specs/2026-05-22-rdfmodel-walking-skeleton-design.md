# RDFModel Walking Skeleton — Design

**Date:** 2026-05-22
**Status:** Approved (brainstorming phase)
**Scope:** §4 of the djangordf project checklist, MVP slice

## 1. Goal

Establish an end-to-end path through djangordf so that a single example
RDFModel class can be defined in Python, persisted to a triple store via
SPARQL, read back, updated, and deleted — all without touching the
existing `export_model_to_rdf` function. This walking skeleton becomes
the foundation that later specs (ontology generation, migrations,
admin/forms integration, reasoning, advanced query lookups) build on.

## 2. Design decisions

The seven decisions that drive the rest of the design, captured here for
future readers:

| # | Decision | Choice |
|---|---|---|
| 1 | URI strategy | Hybrid: auto-mint UUID inside a configured namespace by default, explicit IRI override per instance |
| 2 | Backend abstraction | Abstract `TripleStoreBackend` interface with two shipped implementations: `InMemoryBackend` (rdflib) and `FusekiBackend` (SPARQL 1.1 HTTP) |
| 3 | Model base | Own base class with own metaclass and own property/field system; ORM-shaped public API (`MyModel.objects.create/get/all/filter/save/delete`); independent of `django.db.models.Model` |
| 4 | Named graphs | Configurable per model via `Meta.graph_iri`, default = one shared graph from `settings.DJANGORDF_DEFAULT_GRAPH` |
| 5 | Property types | `DataProperty`, `LangStringProperty`, `ObjectProperty`, `URIProperty`; cardinality (`many=False/True`) configurable per property |
| 6 | Reasoning | None in the MVP — explicit triples only; inference is a follow-up spec |
| 7 | SKOS as default meta layer | Class defaults to `skos:Concept`; property names matching the SKOS convention map (`pref_label`, `alt_label`, `broader`, …) get their SKOS predicate auto-assigned; fully overridable |

## 3. Architecture overview

```
djangordf/
├── __init__.py         # public API re-exports
├── apps.py             # existing
├── conf.py             # settings.DJANGORDF_* reader, backend factory
├── namespaces.py       # NamespaceRegistry, prefix binding, LangString
├── backends/
│   ├── __init__.py
│   ├── base.py         # TripleStoreBackend (abstract)
│   ├── memory.py       # rdflib in-memory implementation
│   └── fuseki.py       # SPARQL 1.1 HTTP implementation
├── models.py           # RDFModel + RDFModelMeta
├── properties.py       # Property base + concrete property types
├── manager.py          # RDFManager + RDFQuerySet
├── skos.py             # SKOS IRIs + DEFAULT_PREDICATES map
└── functions.py        # existing export_model_to_rdf, untouched
```

**Invariants the layering enforces:**

- `backends/` knows nothing about RDFModel — it only sees triples and SPARQL strings.
- `models.py` and `manager.py` know nothing about HTTP — they only see the backend interface.
- `properties.py` are pure declarative descriptors with no lifecycle code.

**Write path:**

```
MyModel(pref_label=LangString("Buch", "de")).save()
  → metaclass-collected property list
  → manager.save(instance) builds a triple list via property.to_rdf()
  → backend.update("DELETE WHERE … ; INSERT DATA { GRAPH ?g { … } }")
  → TripleStoreBackend implementation (Fuseki HTTP or in-memory rdflib)
```

**Read path:**

```
MyModel.objects.get(iri="…")
  → manager builds CONSTRUCT { <iri> ?p ?o } WHERE { GRAPH <g> { … } }
  → backend.query() returns an rdflib.Graph
  → manager dispatches matching triples per property through from_rdf()
  → MyModel instance with populated attributes
```

## 4. Backend interface

```python
# djangordf/backends/base.py
class TripleStoreBackend(ABC):
    @abstractmethod
    def query(self, sparql: str) -> Graph: ...
    @abstractmethod
    def update(self, sparql: str) -> None: ...
    @abstractmethod
    def add(self, triples, graph: URIRef | None = None) -> None: ...
    @abstractmethod
    def remove(self, pattern, graph: URIRef | None = None) -> None: ...
    @abstractmethod
    def clear(self, graph: URIRef | None = None) -> None: ...
```

**`InMemoryBackend`** wraps a single `rdflib.ConjunctiveGraph`. SPARQL
query and update go through rdflib's own engine. Zero network, zero
extra dependencies. Powers all unit tests and the local quickstart.

**`FusekiBackend`** wraps a `requests.Session()`. `query()` POSTs to
`<endpoint>/query`, `update()` POSTs to `<endpoint>/update`. `add()` and
`remove()` translate to `INSERT DATA` / `DELETE WHERE` SPARQL strings.
Works against any SPARQL 1.1 HTTP-conformant store (Fuseki, Blazegraph,
GraphDB, Stardog).

**Backend selection** runs through `djangordf.conf.get_backend()`, which
reads `settings.DJANGORDF_BACKEND` (a dict with a `class` dotted path
plus implementation-specific keys). Default when nothing is configured:
`InMemoryBackend`.

**Out of scope for MVP:** transactions, async backends, connection
pooling beyond what `requests.Session` provides, auth mechanisms other
than HTTP Basic.

## 5. RDFModel + metaclass

```python
# djangordf/models.py
class RDFModelMeta(type):
    def __new__(mcs, name, bases, namespace):
        properties = {}
        for attr, value in list(namespace.items()):
            if isinstance(value, Property):
                value.contribute_to_class(attr)
                properties[attr] = value
        cls = super().__new__(mcs, name, bases, namespace)
        cls._properties = properties
        cls._meta = _build_meta(cls, namespace.get("Meta"))
        if name != "RDFModel":
            cls.objects = RDFManager(cls)
        return cls


class RDFModel(metaclass=RDFModelMeta):
    def __init__(self, *, iri=None, **kwargs):
        self.iri = URIRef(iri) if iri else None
        for name, prop in self._properties.items():
            setattr(self, name, kwargs.get(name, prop.default()))

    def save(self): self.objects.save(self)
    def delete(self): self.objects.delete(self)
```

**`Meta` inner class** consumed by `_build_meta()`:

```python
class Vocabulary(RDFModel):
    pref_label = LangStringProperty(many=True)kate
    broader = ObjectProperty("self", many=True)

    class Meta:
        class_iri = skos.Concept                  # optional
        namespace = "http://judaicalink.org/vocab/"   # optional
        graph_iri = "http://judaicalink.org/graph/vocab"  # optional
```

**Defaults** when `Meta` is silent:

| Field | Fallback |
|---|---|
| `class_iri` | `skos:Concept` |
| `namespace` | `settings.DJANGORDF_DEFAULT_NAMESPACE`, then `urn:djangordf:<modelname>:` |
| `graph_iri` | `settings.DJANGORDF_DEFAULT_GRAPH`, then `urn:djangordf:default` |

Strings starting with a known prefix (e.g. `"skos:Concept"`,
`"foaf:Person"`) are resolved through `NamespaceRegistry.resolve()`.

**IRI minting:**

- `model.iri is None` at save time → `URIRef(namespace + uuid.uuid4().hex)`.
- `model.iri` set explicitly → kept as-is.
- `save()` runs `DELETE WHERE { <iri> ?p ?o }` followed by `INSERT DATA`
  in a single SPARQL update so updates are idempotent and stale triples
  cannot survive.

**Identity:** `__eq__` compares IRIs; instances without an IRI are only
equal to themselves. `__hash__` is `None` until the instance has an IRI.

**Out of scope for MVP:** model inheritance with `rdfs:subClassOf`
generation, `Meta.abstract`, field-level validators beyond type checks,
signals (`pre_save`, `post_save`).

## 6. Property types

```python
# djangordf/properties.py
class Property:
    def __init__(self, predicate=None, *, many=False, required=False, default=None):
        self.predicate = URIRef(predicate) if predicate else None
        self.many = many
        self.required = required
        self._default = default
        self.attr_name = None

    def contribute_to_class(self, attr_name): self.attr_name = attr_name
    def default(self): return [] if self.many else self._default
    def to_rdf(self, value): ...   # subclasses override
    def from_rdf(self, terms): ...  # subclasses override
```

| Property | Python value | RDF serialisation | Example |
|---|---|---|---|
| `DataProperty` | `str` / `int` / `float` / `bool` / `datetime` | `Literal` with the configured XSD datatype | `count = DataProperty(ex.count, datatype=XSD.integer)` |
| `LangStringProperty` | `LangString(value, lang)` dataclass | `Literal(value, lang=lang)` (rdf:langString) | `pref_label = LangStringProperty(many=True)` |
| `ObjectProperty` | `RDFModel` instance or its `iri` | `URIRef(target.iri)` | `broader = ObjectProperty("self", many=True)` |
| `URIProperty` | `str` or `URIRef` | `URIRef(value)` | `exact_match = URIProperty(skos.exactMatch, many=True)` |

**`LangString`** (lives in `djangordf/namespaces.py` so it's importable
without the heavy property module):

```python
@dataclass(frozen=True)
class LangString:
    value: str
    lang: str          # ISO 639-1, e.g. "de", "en", "he"
```

Hashable and comparable by value plus lang so it can sit in sets.

**Cardinality:**

- `many=False` (default): scalar or `None`. If the store returns several
  matching triples (which SPARQL does not order deterministically), one
  is picked arbitrarily and a warning is logged so the inconsistency is
  visible.
- `many=True`: always a list. Write produces one triple per element.
  Read collects all matching triples into a list (order undefined unless
  a future spec adds explicit ordering).

**`ObjectProperty("self", …)`** and string-typed targets in general are
looked up lazily against a process-wide model registry that the
`RDFModelMeta` populates at class-creation time. This makes
self-references and forward references work without import-order
gymnastics.

**Implicit SKOS predicate assignment** in the metaclass:

```python
if isinstance(value, Property) and value.predicate is None:
    if attr_name in skos.DEFAULT_PREDICATES:
        value.predicate = skos.DEFAULT_PREDICATES[attr_name]
    else:
        raise ImproperlyConfigured(
            f"Property '{attr_name}' has no predicate= and "
            f"is not a SKOS convention name."
        )
```

**Out of scope for MVP:** validator chains, `choices=`, FK-like cascade
behaviour, reverse accessors (`term.children` for the inverse of
`broader`).

## 7. Manager + CRUD flow

```python
# djangordf/manager.py
class RDFManager:
    def __init__(self, model_class): ...
    def create(self, **kwargs): ...
    def get(self, iri): ...
    def save(self, instance): ...
    def delete(self, instance): ...
    def all(self): ...
    def filter(self, **kwargs): ...
```

**Save flow:**

1. Mint IRI if `instance.iri is None`.
2. Build a triple list: `(iri, rdf:type, class_iri)` plus the triples
   returned by each property's `to_rdf(value)`.
3. Issue one SPARQL update:
   ```sparql
   WITH <graph_iri>
   DELETE { <iri> ?p ?o } WHERE { <iri> ?p ?o };
   INSERT DATA { GRAPH <graph_iri> { <triples> } }
   ```

**Get flow:**

1. Run `CONSTRUCT { <iri> ?p ?o } WHERE { GRAPH <g> { <iri> ?p ?o } }`.
2. Empty graph → raise `ModelClass.DoesNotExist`.
3. For each declared property, pull out matching triples by predicate
   and dispatch them through `from_rdf()`; assign to attributes.

**`RDFQuerySet`** is lazy. It holds the SPARQL pattern and only
materialises on iteration, `list()`, `len()`. MVP methods:
`__iter__`, `__len__`, `count()`, `first()`. No slicing, no `order_by`
— added when needed.

**`filter(<attr>=<value>)`** in the MVP only supports exact match per
attribute. The manager looks up the predicate IRI through
`model_class._properties[attr].predicate` and appends
`?s <predicate> <value>` to the existing pattern. Lookups
(`__icontains`, `__startswith`, `__gt`) are out of scope for this spec.

**Settings example:**

```python
DJANGORDF_BACKEND = {
    "class": "djangordf.backends.fuseki.FusekiBackend",
    "endpoint": "http://localhost:3030/judaicalink",
}
DJANGORDF_DEFAULT_NAMESPACE = "http://judaicalink.org/data/"
DJANGORDF_DEFAULT_GRAPH = "http://judaicalink.org/graph/default"
DJANGORDF_NAMESPACES = {
    "jl": "http://judaicalink.org/vocab/",
    "gnd": "https://d-nb.info/gnd/",
}
```

**Out of scope for MVP:** `update_or_create`, `get_or_create`,
`bulk_create`, `bulk_update`, transactions, signals, caching.

## 8. SKOS defaults + namespace registry

### `djangordf/namespaces.py`

`NamespaceRegistry` is a per-process registry seeded with the common
prefixes (rdf, rdfs, owl, xsd, skos, dct, foaf). Users register more
through `settings.DJANGORDF_NAMESPACES`, read by
`DjangordfConfig.ready()`. The registry can `bind_to_graph()` a fresh
rdflib Graph so output Turtle is pretty, and `resolve()` a CURIE
(`"skos:Concept"`) into a `URIRef`.

### `djangordf/skos.py`

Re-exports SKOS class and predicate IRIs from rdflib so callers do not
need to know whether a particular constant comes from rdflib or from
us. Also defines `DEFAULT_PREDICATES`, the convention map used by the
metaclass to assign implicit predicates to attribute names like
`pref_label`, `alt_label`, `broader`, etc.

### What the defaults buy users

A working SKOS thesaurus class needs no `predicate=` arguments and no
`Meta.class_iri`:

```python
class Term(RDFModel):
    pref_label = LangStringProperty(many=True)
    alt_label = LangStringProperty(many=True)
    broader = ObjectProperty("self", many=True)
```

Everything is still overridable — CURIEs in `Meta.class_iri` and
explicit `predicate=` keep the framework agnostic.

## 9. Test strategy

| Layer | Backend | What it locks down |
|---|---|---|
| Unit (fast, many) | `InMemoryBackend` | metaclass collection, property serialisation, SKOS default resolution, CURIE resolution, manager CRUD |
| Integration (slow, few) | `FusekiBackend` against a `docker compose` Fuseki | HTTP roundtrip, update idempotence, auth path |
| Existing | unchanged | `export_model_to_rdf` keeps its current tests; no refactor coupling |

The MVP is considered green when all unit tests pass. Fuseki integration
tests live behind a `@pytest.mark.fuseki` marker, default-excluded; a
separate CI job that spins up a Fuseki service container will run them.

### Walking-skeleton acceptance script

```python
from djangordf import RDFModel, LangStringProperty, ObjectProperty
from djangordf.namespaces import LangString


class Term(RDFModel):
    pref_label = LangStringProperty(many=True)
    broader = ObjectProperty("self", many=True)


buch = Term.objects.create(
    pref_label=[LangString("Buch", "de"), LangString("Book", "en")],
)
roman = Term.objects.create(
    pref_label=[LangString("Roman", "de")],
    broader=[buch],
)

reloaded = Term.objects.get(roman.iri)
assert reloaded.broader[0].iri == buch.iri
assert any(ls.lang == "en" and ls.value == "Book" for ls in buch.pref_label)
```

When this script runs green against the default `InMemoryBackend`
without further changes to djangordf, the MVP is done.

### Beweisende Unit-Tests (initial set)

1. `test_create_mints_iri` — `objects.create()` produces an IRI in the configured namespace.
2. `test_save_writes_rdf_type_triple` — `(<iri>, rdf:type, <class_iri>)` is in the store.
3. `test_save_writes_all_properties` — every declared property lands as a triple with the expected predicate.
4. `test_skos_default_predicate_for_pref_label` — a property named `pref_label` without `predicate=` gets `skos:prefLabel`.
5. `test_curie_class_iri_resolves` — `Meta.class_iri = "foaf:Person"` resolves to `FOAF.Person`.
6. `test_get_round_trip` — `create` → `get(iri)` round-trips every property value.
7. `test_save_is_idempotent` — calling `save()` twice on the same instance leaves the triple count unchanged.
8. `test_update_overwrites_stale_triples` — changing a property and calling `save()` removes the previous value.
9. `test_delete_removes_all_triples` — after `delete()`, no `<iri> ?p ?o` triples remain.
10. `test_lang_string_round_trip` — `LangString("Buch", "de")` round-trips through the store.
11. `test_object_property_self_reference` — a `broader` link round-trips and resolves to the target instance's IRI.
12. `test_get_missing_iri_raises_does_not_exist` — `get(iri="…not-here…")` raises `Term.DoesNotExist`.

## 10. Out of scope (collected, for the follow-up specs)

- Server-side or client-side reasoning (RDFS, OWL, SKOS rules).
- Inverse property generation (e.g. auto-write `narrower` when `broader` is set).
- Cross-class queries, joins, ordering, slicing, advanced lookups.
- Ontology generation from models (`subClassOf`, `domain`, `range`).
- Schema-sync migrations into the triple store.
- Django Admin and Forms integration.
- Bulk operations, transactions, signals, caching, async.
- Importing existing SKOS vocabularies (GND, AAT, Wikidata) as read-only sources.
- Hybrid mode with a relational User/Auth model alongside RDFModel domain data.
- Fuseki integration tests in CI by default (marker exists, opt-in only).

## 11. Acceptance criteria

The walking skeleton is done when:

1. All twelve unit tests listed in §9 pass against `InMemoryBackend`.
2. The acceptance script in §9 runs green without modification to djangordf.
3. `flake8 djangordf tests setup.py` is clean.
4. CI runs the new tests on Python 3.10, 3.11, 3.12 alongside the existing test suite.
5. The existing `export_model_to_rdf` tests still pass — no regression in the legacy export path.
