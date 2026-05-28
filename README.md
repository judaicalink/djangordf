# Django RDF

[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://GitHub.com/judaicalink/djangordf/graphs/commit-activity)

[![GitHub license](https://img.shields.io/github/license/Naereen/StrapDown.js.svg)](https://github.com/judaicalink/djangordf/blob/master/LICENSE)

[![forthebadge made-with-python](http://ForTheBadge.com/images/badges/made-with-python.svg)](https://www.python.org/)

![PyPI - Downloads](https://img.shields.io/pypi/dm/djangordf)

![PyPI - Version](https://img.shields.io/pypi/v/djangordf)


**djangordf** is a Django library for managing RDF data with a
declarative model layer. Domain classes are written like Django models
but persist as triples in a SPARQL 1.1 triple store, with built-in
SKOS conventions, language-tagged literals, and a lazy queryset that
mirrors Django's manager API.

## Features

- **`RDFModel`** — declarative base class with `class_iri`,
  `namespace`, and `graph_iri` configured through a `Meta` inner class.
  Defaults to `skos:Concept` and uses the namespace and graph IRIs from
  Django settings.
- **Property types** — `DataProperty` for typed literals,
  `LangStringProperty` for `rdf:langString` (using the `LangString`
  dataclass), `ObjectProperty` for instance-to-instance links (with
  lazy `"self"` and string-name target resolution), and `URIProperty`
  for raw IRIs. Each supports `many=True/False` cardinality.
- **SKOS defaults** — properties named `pref_label`, `alt_label`,
  `broader`, `narrower`, etc. resolve to their SKOS predicates
  automatically; no explicit `predicate=` needed for the conventions.
- **`RDFManager`** + lazy **`RDFQuerySet`** — Django-style
  `objects.create`, `objects.get`, `objects.all`, `objects.filter`.
  `save` is idempotent and overwrites stale triples in a single SPARQL
  update; `delete` strips every triple for the IRI.
- **Backends** — ships an `InMemoryBackend` (rdflib, good for tests and
  local development) and a `FusekiBackend` (SPARQL 1.1 HTTP, works
  against Apache Jena Fuseki, GraphDB, Blazegraph, Stardog).
- **`NamespaceRegistry`** — register prefixes through
  `DJANGORDF_NAMESPACES` and resolve CURIEs like `"skos:Concept"` into
  full `URIRef` objects.
- **Legacy `export_model_to_rdf`** — the original Django-model-to-RDF
  exporter from earlier releases still works unchanged.

## Installation

```bash
pip install djangordf
```

Add the app to `INSTALLED_APPS` and configure a backend:

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "djangordf",
]

DJANGORDF_BACKEND = {
    "class": "djangordf.backends.memory.InMemoryBackend",
}

DJANGORDF_DEFAULT_NAMESPACE = "http://example.org/data/"
DJANGORDF_DEFAULT_GRAPH = "http://example.org/graph/default"

DJANGORDF_NAMESPACES = {
    "ex": "http://example.org/vocab/",
}
```

### Talking to a real triple store

Swap in the Fuseki backend (or any SPARQL 1.1 endpoint):

```python
DJANGORDF_BACKEND = {
    "class": "djangordf.backends.fuseki.FusekiBackend",
    "endpoint": "http://localhost:3030/judaicalink",
    # optional:
    "user": "admin",
    "password": "secret",
}
```

The repository ships a `docker-compose.yml` that boots a local Fuseki
for development; opt-in integration tests behind the `@pytest.mark.fuseki`
marker exercise the HTTP path end-to-end.

## Usage

Define a model:

```python
from djangordf import (
    RDFModel,
    LangStringProperty,
    ObjectProperty,
)
from djangordf.namespaces import LangString


class Term(RDFModel):
    pref_label = LangStringProperty(many=True)
    alt_label = LangStringProperty(many=True)
    broader = ObjectProperty("self", many=True)
```

No `class Meta`, no `predicate=` arguments: `Term` defaults to
`skos:Concept`, and `pref_label` / `alt_label` / `broader` resolve to
their SKOS predicates through the convention map. Mint, query, link:

```python
buch = Term.objects.create(
    pref_label=[LangString("Buch", "de"), LangString("Book", "en")],
)
roman = Term.objects.create(
    pref_label=[LangString("Roman", "de")],
    broader=[buch],
)

reloaded = Term.objects.get(roman.iri)
assert reloaded.broader[0].iri == buch.iri
assert any(
    ls.lang == "en" and ls.value == "Book"
    for ls in buch.pref_label
)
```

`save` is idempotent — calling it twice does not duplicate triples.
Updates overwrite previous values in one SPARQL transaction:

```python
buch.pref_label = [LangString("Buch (überarbeitet)", "de")]
buch.save()
```

Queries return a lazy `RDFQuerySet`; the store is only hit on
iteration, `len`, `count`, or `first`:

```python
for term in Term.objects.all():
    print(term.iri, term.pref_label)

assert Term.objects.filter(broader=buch).count() == 1
```

Explicit predicates and CURIE-based class IRIs are also supported:

```python
from rdflib import URIRef
from rdflib.namespace import XSD

from djangordf import DataProperty, URIProperty


class Person(RDFModel):
    name = DataProperty(
        predicate=URIRef("http://xmlns.com/foaf/0.1/name"),
        datatype=XSD.string,
    )
    homepage = URIProperty(
        predicate=URIRef("http://xmlns.com/foaf/0.1/homepage"),
    )

    class Meta:
        class_iri = "foaf:Person"   # resolved via NamespaceRegistry
        namespace = "http://example.org/people/"
        graph_iri = "http://example.org/graph/people"
```

### Walking-skeleton example

A self-contained, runnable end-to-end example lives at
[`examples/walking_skeleton.py`](examples/walking_skeleton.py). It
mirrors the design spec's acceptance script and exits 0 against the
default in-memory backend:

```bash
python examples/walking_skeleton.py
```

### Legacy Django-to-RDF export

The original `export_model_to_rdf(QuerySet, ...)` function is still
available for one-shot dumps of relational Django data into a Turtle
file; see `djangordf/functions.py` and the existing tests in
`tests/test_export.py`.

## Settings reference

| Setting | Purpose | Default |
|---|---|---|
| `DJANGORDF_BACKEND` | Triple-store backend config (dict with `class` plus kwargs) | In-memory backend |
| `DJANGORDF_DEFAULT_NAMESPACE` | Used to mint IRIs when `Meta.namespace` is silent | `urn:djangordf:<model>:` |
| `DJANGORDF_DEFAULT_GRAPH` | Used when `Meta.graph_iri` is silent | `urn:djangordf:default` |
| `DJANGORDF_NAMESPACES` | `prefix -> uri` map read into the `NamespaceRegistry` at app ready | `{}` |

## License

This project is licensed under the MIT License.
