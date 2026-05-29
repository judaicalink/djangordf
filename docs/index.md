# djangordf

A Django library for managing RDF data with a declarative model layer.
Domain classes are written like Django models but persist as triples
in a SPARQL 1.1 triple store, with built-in SKOS conventions,
language-tagged literals, and a lazy queryset that mirrors Django's
manager API.

## Why djangordf

- **Familiar surface.** `Term.objects.create(...)`, `Term.objects.get(iri)`,
  `Term.objects.filter(...)` — the manager API mirrors `django.db.models`.
- **RDF native.** Storage is triples in a real SPARQL 1.1 store
  (Apache Jena Fuseki, GraphDB, Blazegraph, Stardog, or the
  in-process rdflib backend for tests and local development).
- **SKOS by default.** Properties named `pref_label`, `broader`,
  `definition`, etc. resolve to their SKOS predicates automatically;
  no boilerplate `predicate=` arguments needed for the conventions.
- **Language-tagged literals.** First-class support for
  `rdf:langString` via the `LangString(value, lang)` dataclass.
- **Round-trips.** `save()` is idempotent and overwrites stale
  triples in a single SPARQL update; `delete()` strips every triple
  for the IRI.

## Contents

```{toctree}
:maxdepth: 2

installation
quickstart
settings
api/index
```

## Project links

- [Source code](https://github.com/judaicalink/djangordf)
- [PyPI](https://pypi.org/project/djangordf/)
- [Issue tracker](https://github.com/judaicalink/djangordf/issues)
- [Changelog](https://github.com/judaicalink/djangordf/blob/main/CHANGELOG.md)
