# Settings

All djangordf settings live alongside the rest of Django's
configuration. None of them are required to be set explicitly — the
package falls back to safe in-memory defaults so that importing
djangordf in a fresh Django project always works.

## `DJANGORDF_BACKEND`

**Type:** `dict` with a mandatory `class` key plus any keyword
arguments forwarded to the backend's constructor.
**Default:** in-memory backend (`djangordf.backends.memory.InMemoryBackend`).

```python
DJANGORDF_BACKEND = {
    "class": "djangordf.backends.fuseki.FusekiBackend",
    "endpoint": "http://localhost:3030/judaicalink",
}
```

The dotted import path is resolved through Django's
`import_string`. Anything other than `class` is forwarded as kwargs to
the backend, so you can pass `endpoint`, `user`, `password`, or any
custom backend constructor argument.

## `DJANGORDF_DEFAULT_NAMESPACE`

**Type:** `str`.
**Default:** `"urn:djangordf:<modelname>:"` (built per-class).

Used to mint IRIs when a model does not declare `Meta.namespace`. The
manager appends a `uuid4().hex` to this value to produce a fresh IRI
per `objects.create(...)` call.

```python
DJANGORDF_DEFAULT_NAMESPACE = "http://example.org/data/"
```

## `DJANGORDF_DEFAULT_GRAPH`

**Type:** `str`.
**Default:** `"urn:djangordf:default"`.

Named graph IRI written to when a model does not declare
`Meta.graph_iri`. Every `save` and `delete` issues SPARQL updates
scoped to this graph.

```python
DJANGORDF_DEFAULT_GRAPH = "http://example.org/graph/default"
```

## `DJANGORDF_NAMESPACES`

**Type:** `dict[str, str]` mapping prefix to namespace URI.
**Default:** `{}` (only the seeded prefixes — `rdf`, `rdfs`, `owl`,
`xsd`, `skos`, `dct`, `foaf` — are available).

Read by `DjangordfConfig.ready()` and merged into the module-level
{class}`djangordf.namespaces.NamespaceRegistry`. Once registered, the
prefix can be used in `Meta.class_iri` (`"jl:Concept"`) or anywhere
the registry's `resolve()` is called.

```python
DJANGORDF_NAMESPACES = {
    "jl": "http://judaicalink.org/vocab/",
    "gnd": "https://d-nb.info/gnd/",
}
```

## Putting it together

A typical project's settings block looks like this:

```python
INSTALLED_APPS = [
    # ...
    "djangordf",
]

DJANGORDF_BACKEND = {
    "class": "djangordf.backends.fuseki.FusekiBackend",
    "endpoint": "http://localhost:3030/judaicalink",
}
DJANGORDF_DEFAULT_NAMESPACE = "http://judaicalink.org/data/"
DJANGORDF_DEFAULT_GRAPH = "http://judaicalink.org/graph/default"
DJANGORDF_NAMESPACES = {
    "jl": "http://judaicalink.org/vocab/",
}
```
