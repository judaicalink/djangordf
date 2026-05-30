# Ontology Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `djangordf.ontology.generate_ontology()` and the matching `python manage.py dump_ontology` management command, both of which emit an OWL ontology derived from the declared `RDFModel` classes. Closes GitHub issue #26.

**Architecture:** A new pure-function `generate_ontology(models=None, graph=None) -> rdflib.Graph` walks the model registry, asks each class for its declared properties, and emits per-class + per-property triples (`owl:Class`, `rdfs:subClassOf`, `rdfs:label`, `rdfs:comment`, `owl:DatatypeProperty`/`owl:ObjectProperty`, `rdfs:domain`, `rdfs:range`, blank-node `owl:Restriction`s for cardinality). External predicates (those whose namespace matches one of the seeded `NamespaceRegistry` prefixes — `rdf`, `rdfs`, `owl`, `xsd`, `skos`, `dct`, `foaf`) are recognised and **not** re-declared as `owl:*Property`; we only attach per-class `rdfs:domain`/`rdfs:range`/cardinality statements to them. The Django management command `dump_ontology` is a thin wrapper that calls the function and serialises the resulting graph; format selection happens through `rdflib`'s native serialisers so users get Turtle / RDF/XML / JSON-LD / N3 for free.

**Tech stack:** Python 3.10+, rdflib 7.x, Django 3.2+, pytest 9.x, pytest-django 4.x.

**Spec reference:** [docs/superpowers/specs/2026-05-22-rdfmodel-walking-skeleton-design.md](../specs/2026-05-22-rdfmodel-walking-skeleton-design.md) §10 (out-of-scope follow-up).

**Issue:** [#26 Generate an OWL ontology from declared RDFModel classes](https://github.com/judaicalink/djangordf/issues/26).

---

## File structure

| Path | Responsibility | Action |
|---|---|---|
| `djangordf/ontology.py` | `generate_ontology()` plus private helpers | new |
| `djangordf/management/__init__.py` | package marker | new |
| `djangordf/management/commands/__init__.py` | package marker | new |
| `djangordf/management/commands/dump_ontology.py` | Django command wrapping the function | new |
| `djangordf/__init__.py` | re-export `generate_ontology` | edit |
| `tests/test_ontology.py` | unit tests of the function | new |
| `tests/test_dump_ontology_command.py` | tests of the command | new |
| `docs/api/ontology.md` | autodoc page for the new module | new |
| `docs/api/index.md` | add ontology to the toc | edit |
| `docs/quickstart.md` | brief mention of `dump_ontology` | edit |

---

## Tasks

### Task 1 — External-namespace detection

- [ ] In `djangordf/ontology.py`, expose `_EXTERNAL_PREFIXES = frozenset(["rdf", "rdfs", "owl", "xsd", "skos", "dct", "foaf"])` and a helper `_is_external_predicate(predicate)` that asks `registry.bindings()` whether the IRI starts with any of these namespaces' URIs.

### Task 2 — Class-level triples

- [ ] `_emit_class(graph, model)` — emit `(class_iri, RDF.type, OWL.Class)`, `(class_iri, RDFS.label, Literal(model.__name__))`, and `(class_iri, RDFS.comment, Literal(first_line))` when `model.__doc__` exists.
- [ ] `_emit_subclass_of(graph, model)` — walk `model.__mro__[1:]`, skip `RDFModel` itself and `object`, and emit `(class_iri, RDFS.subClassOf, base.class_iri)` for any other class whose `_meta` carries a `class_iri`.

### Task 3 — Property-level triples

- [ ] `_emit_property_declaration(graph, prop)` — only when the predicate is **not** external; emit `(predicate, RDF.type, OWL.DatatypeProperty)` for `DataProperty`/`LangStringProperty` and `(predicate, RDF.type, OWL.ObjectProperty)` for `ObjectProperty`/`URIProperty`; plus `(predicate, RDFS.label, Literal(attr_name))`.
- [ ] `_emit_property_domain_range(graph, model, prop)` — emit `(predicate, RDFS.domain, class_iri)` always; emit `RDFS.range` based on property type:
      - `DataProperty.datatype` (fallback `XSD.string`).
      - `LangStringProperty` → `RDF.langString`.
      - `ObjectProperty` → `target_class._meta.class_iri`.
      - `URIProperty` → `RDFS.Resource`.
- [ ] `_emit_cardinality_restriction(graph, model, prop)` — when `required=True` OR `many=False`, mint a fresh `BNode()` per restriction, attach as `(class_iri, RDFS.subClassOf, _bnode)`, then add `(_bnode, RDF.type, OWL.Restriction)`, `(_bnode, OWL.onProperty, predicate)`, and the cardinality assertion (`OWL.minCardinality 1` for required, `OWL.maxCardinality 1` for `many=False`). Both can fire on the same property — emit two restrictions.

### Task 4 — Public function

- [ ] `generate_ontology(models=None, graph=None) -> Graph` — default `models` to `list(djangordf.models._MODEL_REGISTRY.values())`; default `graph` to a fresh `Graph()`; call `registry.bind_to_graph(graph)` so Turtle output is pretty; iterate `models` and dispatch through the helpers.

### Task 5 — Management command

- [ ] `djangordf/management/commands/dump_ontology.py`:
      - `BaseCommand` with `add_arguments` for `--output PATH` (default `-` for stdout) and `--format` (choices `turtle`, `xml`, `json-ld`, `n3`; default `turtle`).
      - In `handle`: build the graph, serialise, write to file or `self.stdout.write`.

### Task 6 — Re-exports + docs

- [ ] `djangordf/__init__.py`: import + `__all__` entry for `generate_ontology`.
- [ ] `docs/api/ontology.md` autodoc page.
- [ ] `docs/api/index.md` ToC entry.
- [ ] `docs/quickstart.md` short paragraph at the end showing `dump_ontology`.

### Task 7 — Tests

- [ ] `tests/test_ontology.py`:
      - `test_empty_registry_returns_graph_with_only_prefix_bindings`.
      - `test_model_class_emits_owl_class_triple`.
      - `test_class_label_uses_class_name`.
      - `test_class_comment_uses_first_line_of_docstring`.
      - `test_no_comment_when_class_has_no_docstring`.
      - `test_subclass_relationship_emits_rdfs_subclassof`.
      - `test_custom_dataproperty_declared_as_owl_datatype_property`.
      - `test_custom_objectproperty_declared_as_owl_object_property`.
      - `test_uriproperty_declared_as_owl_object_property`.
      - `test_langstring_property_uses_rdf_langstring_range`.
      - `test_dataproperty_range_defaults_to_xsd_string`.
      - `test_objectproperty_range_is_target_class_iri`.
      - `test_external_predicate_not_redeclared`.
      - `test_external_predicate_still_gets_domain_and_range`.
      - `test_required_property_emits_min_cardinality_restriction`.
      - `test_many_false_property_emits_max_cardinality_restriction`.
      - `test_many_true_not_required_emits_no_restriction`.
      - `test_graph_has_prefix_bindings_from_registry`.
- [ ] `tests/test_dump_ontology_command.py`:
      - `test_command_writes_turtle_to_stdout` — capture and parse round-trip.
      - `test_command_writes_to_output_file` (tmp_path fixture).
      - `test_command_respects_format_xml`.

### Task 8 — Lint, test, push

- [ ] `flake8 djangordf tests setup.py examples docs/conf.py` clean.
- [ ] `pytest -q` — green; expect ~21 new tests, total ≈ 172.
- [ ] Commit per repo convention. Push branch. Open PR against `development` referencing #26.

---

## Done when

- `generate_ontology()` covers every acceptance bullet from #26.
- `python manage.py dump_ontology` round-trips through `rdflib.Graph().parse()`.
- New docs page exists; autodoc renders without warnings under `sphinx-build -W`.
- PR merged; issue #26 closed.
