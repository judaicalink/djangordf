# Installation

## Install the package

```bash
pip install djangordf
```

djangordf requires Python 3.8+ and pulls in Django ≥ 3.2 and rdflib
≥ 6.0 as runtime dependencies.

## Wire it into Django

Add `djangordf` to `INSTALLED_APPS` and configure at least a backend:

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
```

That is enough to start declaring `RDFModel` subclasses and running the
quickstart against the in-memory backend.

## Talking to a real triple store

Swap the backend setting for a SPARQL 1.1 HTTP endpoint:

```python
DJANGORDF_BACKEND = {
    "class": "djangordf.backends.fuseki.FusekiBackend",
    "endpoint": "http://localhost:3030/judaicalink",
    # optional:
    "user": "admin",
    "password": "secret",
}
```

The `FusekiBackend` works against Apache Jena Fuseki out of the box
and against any other store that speaks the SPARQL 1.1 Protocol —
including GraphDB, Blazegraph, and Stardog. The repository ships a
`docker-compose.yml` that boots a local Fuseki instance for
development.

## Optional: register your own prefixes

If you want to use CURIEs in `Meta.class_iri` (e.g. `"foaf:Person"`) or
reference your own vocabulary by prefix, register them in settings:

```python
DJANGORDF_NAMESPACES = {
    "jl": "http://judaicalink.org/vocab/",
    "gnd": "https://d-nb.info/gnd/",
}
```

The {class}`djangordf.namespaces.NamespaceRegistry` is seeded with
`rdf`, `rdfs`, `owl`, `xsd`, `skos`, `dct`, and `foaf` out of the box,
so those prefixes always resolve.

## Verify the install

Run the bundled walking-skeleton script:

```bash
python examples/walking_skeleton.py
```

If it exits 0 without output, the package is wired up correctly.
