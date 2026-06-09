# Inverse Properties Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `inverse=` support to `ObjectProperty` so declarations like `broader = ObjectProperty("self", inverse="narrower")` produce **both** directions in the triple store on save (mirror semantics) and `Term.objects.get(parent.iri).narrower` returns the children without an extra SPARQL roundtrip per property. The ontology generator emits a matching `owl:inverseOf` triple when both ends declare each other. Closes GitHub issue #34.

**Architecture:** `ObjectProperty` stores the inverse attribute name verbatim and resolves it lazily — same shape as the existing `target` resolution — into an `inverse_property` (the `Property` object on the target class) and `inverse_predicate` (its `URIRef`). The metaclass does **not** need to know about inverses at class-creation time. Manager-side mirror semantics happen inside `RDFManager.save` and `RDFManager.delete`: both methods compose a multi-statement SPARQL update that (a) deletes stale forward triples on the subject, (b) deletes stale mirror triples whose **object** is the subject and whose **predicate** is the configured inverse, (c) re-inserts forward + mirror triples in a single `INSERT DATA` block. The ontology generator gains one extra pass that looks for reciprocal `inverse=` declarations and emits `(predicate, owl:inverseOf, inverse_predicate)`; we emit each pair once (lexicographic predicate IRI ordering) so the output is stable.

**Tech stack:** Python 3.10+, rdflib 7.x, Django 3.2+, pytest 9.x, pytest-django 4.x.

**Spec reference:** [docs/superpowers/specs/2026-05-22-rdfmodel-walking-skeleton-design.md](../specs/2026-05-22-rdfmodel-walking-skeleton-design.md) §10 (out-of-scope follow-up).

**Issue:** [#34 Support inverse properties on ObjectProperty](https://github.com/judaicalink/djangordf/issues/34).

---

## File structure

| Path | Responsibility | Action |
|---|---|---|
| `djangordf/properties.py` | `ObjectProperty(inverse=...)` keyword + lazy resolution | extend |
| `djangordf/manager.py` | mirror semantics in `save` and `delete` | extend |
| `djangordf/ontology.py` | emit `owl:inverseOf` for declared pairs | extend |
| `tests/test_properties.py` | resolution unit tests | extend |
| `tests/test_inverse_properties.py` | end-to-end mirror behaviour | new |
| `tests/test_ontology.py` | `owl:inverseOf` emission | extend |
| `docs/quickstart.md` | show `inverse="narrower"` in the worked example | extend |
| `docs/superpowers/plans/2026-06-09-inverse-properties.md` | this plan | new |

---

## Tasks

### Task 1 — `ObjectProperty.inverse` plumbing

- [ ] `ObjectProperty.__init__` accepts `inverse: Optional[str] = None` and stores it.
- [ ] `inverse_property` property: returns `target_class._properties[self.inverse]`. Raises `ValueError(f"inverse {self.inverse!r} is not declared on {target_class.__name__}")` if unresolved.
- [ ] `inverse_predicate` property: returns `inverse_property.predicate`.
- [ ] Both accessors are lazy (no eager class-creation-time lookup); raise on the first call when misconfigured.

### Task 2 — Manager save: mirror writes

- [ ] In `RDFManager.save`, after building the forward triple list, gather every property with `inverse=`:
      - For each related target (single or `many=True`), build `(target.iri, inverse_predicate, self.iri)` triples and add them to the SPARQL body.
      - Build a `DELETE WHERE { ?s <inverse_predicate> <self.iri> }` statement for each distinct inverse predicate the model uses, so stale mirror triples disappear when relationships change.
- [ ] The composed SPARQL update is one block:
      ```sparql
      WITH <graph_iri>
      DELETE { <self.iri> ?p ?o } WHERE { <self.iri> ?p ?o } ;
      DELETE { ?s <inv1> <self.iri> } WHERE { ?s <inv1> <self.iri> } ;
      DELETE { ?s <inv2> <self.iri> } WHERE { ?s <inv2> <self.iri> } ;
      INSERT DATA { GRAPH <graph_iri> { <forward triples> <mirror triples> } }
      ```
- [ ] Skip the extra `DELETE`s when the model has no inverse-declaring properties (no behaviour change for existing models).

### Task 3 — Manager delete: mirror strips

- [ ] In `RDFManager.delete`, after the existing `DELETE WHERE { <self.iri> ?p ?o }`, append one `DELETE WHERE { ?s <inv> <self.iri> }` per inverse predicate the model declares.

### Task 4 — Ontology: `owl:inverseOf`

- [ ] Collect declared pairs: for each `ObjectProperty` with `inverse=`, resolve its inverse predicate; emit `(predicate, owl:inverseOf, inverse_predicate)`.
- [ ] Deduplicate symmetrically: emit each pair only once, keyed by `sorted((predicate, inverse_predicate))`.

### Task 5 — Tests

Property-level unit tests in `tests/test_properties.py`:

- [ ] `test_object_property_inverse_keyword_stored_verbatim`.
- [ ] `test_object_property_inverse_property_resolves`.
- [ ] `test_object_property_inverse_predicate_resolves`.
- [ ] `test_object_property_inverse_unknown_attribute_raises_value_error`.
- [ ] `test_object_property_inverse_none_default`.

End-to-end mirror behaviour in `tests/test_inverse_properties.py` (against `InMemoryBackend`, mirroring the style of the existing `test_manager.py`):

- [ ] `test_save_writes_both_directions`.
- [ ] `test_target_attribute_reads_mirror_after_save`.
- [ ] `test_update_strips_stale_mirror_on_previous_parent`.
- [ ] `test_delete_strips_mirror_triples`.
- [ ] `test_many_inverse_writes_each_parent`.
- [ ] `test_inverse_only_on_one_side_still_mirrors_writes`.

Ontology tests in `tests/test_ontology.py`:

- [ ] `test_owl_inverseof_emitted_for_reciprocal_declarations`.
- [ ] `test_owl_inverseof_emitted_only_once_per_pair`.

### Task 6 — Docs

- [ ] `docs/quickstart.md`: extend the `Term` example to use `inverse="narrower"` and show that `parent.narrower` works after a child save.

### Task 7 — Lint, test, push

- [ ] `flake8 djangordf tests setup.py examples docs/conf.py` clean.
- [ ] `pytest -q` — green; expect ~13 new tests, total ≈ 191.
- [ ] `sphinx-build -W -b html docs docs/_build/html` exits 0.
- [ ] Logical commits per the repo convention (English commit messages, no Claude attribution).
- [ ] Push branch, open PR against `development` linking issue #34.

---

## Done when

- All acceptance bullets on #34 pass.
- Existing 178 tests stay green; new tests added.
- Sphinx strict build green.
- PR merged; issue #34 closed.
