# Quickstart

## Declare a model

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

No `class Meta` and no `predicate=` arguments are needed for this
example: `Term` defaults to `skos:Concept`, and the three properties
match the SKOS convention map so the metaclass wires them to
`skos:prefLabel`, `skos:altLabel`, and `skos:broader` automatically.

## Bidirectional links via `inverse=`

For SKOS-style hierarchies you usually want both directions of the
hierarchy stored in the triple store so external tools see them. Add
a `narrower` property and link the two with `inverse=`:

```python
class Term(RDFModel):
    pref_label = LangStringProperty(many=True)
    broader = ObjectProperty("self", many=True, inverse="narrower")
    narrower = ObjectProperty("self", many=True, inverse="broader")
```

Now every `save()` writes both directions in a single SPARQL update,
and `parent.narrower` reads the back-pointers without an extra round
trip:

```python
parent = Term.objects.create()
child = Term.objects.create(broader=[parent])

reloaded = Term.objects.get(parent.iri)
assert reloaded.narrower[0].iri == child.iri
```

Updating `child.broader` to a different parent automatically strips
the stale `narrower` back-pointer from the previous one; deleting the
child removes both directions.

## Create, link, fetch

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

`objects.create(...)` mints an IRI in `DJANGORDF_DEFAULT_NAMESPACE`,
persists the triples in one SPARQL update, and returns the
freshly-built instance. `objects.get(iri)` runs a
`CONSTRUCT { <iri> ?p ?o }`, hydrates the declared properties through
each property's `from_rdf` method, and raises `Term.DoesNotExist` if
the IRI is unknown.

## Update and delete

`save()` is idempotent — calling it twice never duplicates triples —
and overwrites previous values in one SPARQL transaction:

```python
buch.pref_label = [LangString("Buch (überarbeitet)", "de")]
buch.save()
```

`delete()` strips every triple with the instance's IRI as subject:

```python
roman.delete()
```

## Query lazily

`objects.all()` and `objects.filter(**kwargs)` return an
{class}`djangordf.manager.RDFQuerySet`. The store is only hit on
iteration, `len`, `count`, or `first`:

```python
for term in Term.objects.all():
    print(term.iri, term.pref_label)

assert Term.objects.filter(broader=buch).count() == 1
```

Filter values can be Python literals, `URIRef`/`Literal`/`BNode`
instances, or other `RDFModel` instances (the manager will use their
`iri`).

### Cross-class lookups

Filter keys may span `ObjectProperty` hops using Django's `__`
separator. Each segment names a property on the current class;
non-terminal segments must be `ObjectProperty` instances (so the
path can traverse the link); the terminal segment provides the
predicate and the value to compare against.

```python
from djangordf.namespaces import LangString

# One hop: find every Term whose broader has pref_label "Buch"@de.
Term.objects.filter(broader__pref_label=LangString("Buch", "de"))

# Two hops: chain ObjectProperty links arbitrarily deep.
Term.objects.filter(broader__broader__title="Grand")

# Cross-class lookups compose with the existing single-segment form.
Term.objects.filter(broader__title="A", title="ChildOfA")
```

Each hop adds one triple pattern to the underlying SPARQL `SELECT
DISTINCT ?s` and intermediate variables (`?v1`, `?v2`, …) are minted
automatically. Lookup suffixes (`__icontains`, `__startswith`,
`__gt`, …) are deliberately out of scope for this release — every
segment compares for exact equality at the terminal step.

## Custom predicates and CURIE class IRIs

When the SKOS conventions do not fit, pass explicit predicates and use
CURIEs in `Meta.class_iri`:

```python
from rdflib import URIRef
from rdflib.namespace import XSD

from djangordf import DataProperty, RDFModel, URIProperty


class Person(RDFModel):
    name = DataProperty(
        predicate=URIRef("http://xmlns.com/foaf/0.1/name"),
        datatype=XSD.string,
    )
    homepage = URIProperty(
        predicate=URIRef("http://xmlns.com/foaf/0.1/homepage"),
    )

    class Meta:
        class_iri = "foaf:Person"   # resolved via the NamespaceRegistry
        namespace = "http://example.org/people/"
        graph_iri = "http://example.org/graph/people"
```

## The walking-skeleton example

A self-contained, runnable end-to-end example lives at
`examples/walking_skeleton.py` in the repository. It mirrors the
design spec's acceptance script and exits 0 against the default
in-memory backend, which makes it the fastest way to confirm a fresh
install works.

## Dump the schema as an OWL ontology

Once your models are declared, you can publish the schema as Turtle
(or RDF/XML, JSON-LD, N3) directly from the registered classes:

```bash
python manage.py dump_ontology --output schema.ttl
python manage.py dump_ontology --format json-ld > schema.jsonld
```

Programmatic access goes through {func}`djangordf.ontology.generate_ontology`,
which returns an `rdflib.Graph` containing the `owl:Class`,
`rdfs:subClassOf`, `rdfs:domain`/`rdfs:range`, and cardinality
restriction triples derived from your `RDFModel` declarations.
