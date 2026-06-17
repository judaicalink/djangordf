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
automatically.

### Lookup suffixes

The terminal segment can carry a Django-style suffix that turns the
comparison into a SPARQL `FILTER(...)` clause:

```python
# Case-insensitive substring search.
Term.objects.filter(title__icontains="buch")

# Set membership.
Term.objects.filter(count__in=[1, 2, 3])

# Numeric comparisons (typed-literal aware).
Term.objects.filter(count__gt=4)

# Suffixes compose with cross-class spans.
Term.objects.filter(broader__title__icontains="parent")
```

Available suffixes:

- `__exact` (default) — bound triple, exact equality.
- `__iexact`, `__contains`, `__icontains`, `__startswith`,
  `__istartswith`, `__endswith`, `__iendswith` — string matchers,
  the `i` variants compare lowercased.
- `__in` — value is an iterable; emits `?v IN (...)`.
- `__gt`, `__gte`, `__lt`, `__lte` — comparisons; the value is
  serialised through the property's datatype so
  `count__gt=4` produces `"4"^^xsd:integer` in SPARQL.
- `__regex`, `__iregex` — POSIX regex match via SPARQL `REGEX`; the
  `i` variant adds the case-insensitive flag.
- `__isnull` — boolean; `True` matches subjects that have no triple
  for this predicate (`FILTER NOT EXISTS`), `False` matches those
  that do.
- `__year`, `__month`, `__day`, `__hour`, `__minute`, `__second` —
  extract the part from an `xsd:dateTime` literal via SPARQL's
  `YEAR()` / `MONTH()` / `DAY()` / `HOURS()` / `MINUTES()` /
  `SECONDS()` builtins and compare against an integer.

Suffix detection is conservative: a suffix is recognised only when
the key has at least two `__`-separated segments. A model that
happens to declare a property called `exact` (or any other suffix
name) keeps treating it as a property — `filter(exact="x")` is a
single-segment key, so nothing is peeled.

### Reverse-relation navigation

`ObjectProperty(reverse=True)` declares a **read-only** virtual
property: the triples live on a *different* class's forward
predicate, and djangordf reads them "from the other end". Typical
example: every `Book` has an `author`, and you want to navigate from
an `Author` to their books without writing two predicates by hand:

```python
from rdflib import URIRef
from djangordf import DataProperty, ObjectProperty, RDFModel


class Book(RDFModel):
    title = DataProperty(predicate=URIRef("http://example.org/title"))
    author = ObjectProperty(
        "Author", predicate=URIRef("http://example.org/author"),
    )


class Author(RDFModel):
    books = ObjectProperty(
        Book,
        predicate=URIRef("http://example.org/author"),
        many=True,
        reverse=True,
    )
```

Now `Author.objects.get(...)` hydrates `author.books` for free
(djangordf issues a second CONSTRUCT for triples where the IRI is
the *object*), and the filter path-walker swaps subject/object on
any `reverse=True` segment:

```python
# Find authors who have a book whose title contains "cats".
Author.objects.filter(books__title__icontains="cats")
```

`reverse=True` is mutually exclusive with `inverse=...` (which
implies mirror writes — that contradicts read-only) and skips the
SKOS-convention map: you always pass an explicit `predicate=`.

### Composing filters with `Q`

`Q` objects let you combine filter expressions with `|` (OR), `&`
(AND), and `~` (NOT). Pass them positionally to `filter()` alongside
or instead of the usual kwargs:

```python
from djangordf import Q

# OR — SPARQL UNION.
Term.objects.filter(Q(title="A") | Q(title="B"))

# NOT — SPARQL FILTER NOT EXISTS.
Term.objects.filter(~Q(title="bad"))

# Mixing positional Q and kwargs — AND-combined.
Term.objects.filter(Q(title="A") | Q(title="B"), count__gt=5)

# Nested expressions.
Term.objects.filter(
    (Q(title="A") | Q(title="B")) & ~Q(count=1)
)
```

Every `(key, value)` leaf inside a `Q` uses the same key syntax as
flat `filter()`: simple attrs, `__`-separated paths through
`ObjectProperty` hops, the 13 lookup suffixes, and reverse segments
all compose with `Q` exactly as they do with kwargs.

`Q()` with no arguments raises `ValueError`, and `bool(Q(...))`
raises `TypeError` (to avoid silent coercions). Use only the
operators above.

### Ordering and slicing

`order_by(*fields)` chains onto any queryset and emits a SPARQL
`ORDER BY` on materialisation. Prefix a field with `-` for
descending; pass no arguments to clear any existing ordering.

```python
ordered = Term.objects.all().order_by("title")
descending = Term.objects.all().order_by("-count")
multi = Term.objects.all().order_by("title", "-count")
```

Slicing returns a new lazy queryset configured with SPARQL `LIMIT`
and `OFFSET`. Indexing materialises and returns a single instance:

```python
first_ten = Term.objects.all().order_by("count")[:10]
page2 = Term.objects.filter(title__icontains="a").order_by("title")[10:20]
top = Term.objects.all().order_by("-count")[0]   # forces materialisation
```

Negative indices and slice steps raise (`IndexError` / `TypeError`);
chained slices compose correctly so `qs[10:20][2:4]` ends up as
`OFFSET 12 LIMIT 2`. Cross-class ordering (`order_by("broader__title")`)
is intentionally not supported in this release.

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

## Importing external SKOS vocabularies

Read-only RDF dumps from GND, AAT, Wikidata, or any other source can
be ingested into the configured triple store via
{func}`djangordf.load_skos`. By default the triples land in a separate
named graph (`urn:djangordf:external` unless
`DJANGORDF_EXTERNAL_GRAPH` overrides it) so external data stays
isolated from `RDFModel`-managed data.

```python
from djangordf import load_skos, load_external_concept

# From a local file (format inferred from the extension).
n = load_skos("vocab.ttl")

# From a URL (HTTP GET with content negotiation).
n = load_skos("https://example.org/skos/buch.ttl")

# Dereference a single concept IRI directly.
n = load_external_concept("https://d-nb.info/gnd/4001577-9")

# Override the format when the extension lies.
n = load_skos("vocab.bin", format="turtle")

# Direct an explicit named graph (overrides DJANGORDF_EXTERNAL_GRAPH).
n = load_skos("vocab.ttl", graph="http://example.org/imported")
```

Each call returns the number of triples written. The loader accepts
HTTP/HTTPS URLs, filesystem paths, and in-memory `rdflib.Graph`
instances. Without an explicit `backend=`, the same process-wide
backend that `RDFManager` uses receives the writes.

## Bulk operations and signals

`RDFManager` exposes three bulk write paths that issue a single
SPARQL update for many instances at once, and four
`django.dispatch.Signal` instances for hooking into the single-
instance persistence path.

```python
from djangordf import (
    pre_save, post_save, pre_delete, post_delete,
)

# Bulk create — one INSERT DATA for the whole batch.
Term.objects.bulk_create([
    Term(title="A"),
    Term(title="B"),
    Term(title="C"),
])

# Bulk update — one multi-statement SPARQL update.
a.title = "new-A"
b.title = "new-B"
Term.objects.bulk_update([a, b])

# Bulk delete.
Term.objects.bulk_delete([a, b])

# Signals.
def log_save(sender, instance, **kwargs):
    print(f"saved {instance.iri}")

post_save.connect(log_save, sender=Term)
```

Two limitations matched to Django's conventions:

- **Bulk operations do not fire signals.** If you need
  `pre_save` / `post_save` semantics for every instance, use the
  single-instance `save()` path.
- **Bulk operations do not emit `ObjectProperty(inverse=...)` mirror
  triples.** Models that declare an inverse should keep using
  per-instance `save()` for now; the bulk path treats the supplied
  triples as authoritative.

## Hybrid mode: relational auth alongside RDF data

`RDFModel` and `django.db.models.Model` coexist freely. The two layers
talk to different storage backends — the relational ORM to your
configured `DATABASES`, djangordf to the configured
`DJANGORDF_BACKEND` — so adding `djangordf` to `INSTALLED_APPS`
alongside `django.contrib.auth` and `django.contrib.contenttypes` is
the default configuration, not a special mode.

The interesting question is how to link them. The recommended
pattern encodes the relational primary key as a synthetic IRI under
a documented namespace:

```python
from rdflib import URIRef
from djangordf import LangStringProperty, RDFModel, URIProperty
from djangordf.namespaces import LangString


USER_NS = "urn:djangordf:user:"


class Term(RDFModel):
    pref_label = LangStringProperty(many=True)
    created_by = URIProperty(
        predicate=URIRef("http://purl.org/dc/terms/creator"),
    )


# Persist the relational pk as an IRI on the RDF side.
term = Term.objects.create(
    pref_label=[LangString("Buch", "de")],
    created_by=URIRef(f"{USER_NS}{request.user.pk}"),
)

# Round-trip and recover the pk.
reloaded = Term.objects.get(term.iri)
recovered_pk = int(str(reloaded.created_by).removeprefix(USER_NS))
user = User.objects.get(pk=recovered_pk)
```

For the inverse direction — a relational model that stores the IRI of
the RDF concept it points at — use a plain `URLField` or `TextField`:

```python
class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    concept_iri = models.URLField(max_length=500)

    def concept(self):
        from djangordf import RDFModel
        return Term.objects.get(self.concept_iri)
```

A runnable end-to-end version of the first pattern lives at
`examples/hybrid_mode.py`.

## Django admin for RDFModel

`djangordf.admin` provides a Django-admin-style UI for `RDFModel`
classes. Because `RDFModel` is not a `django.db.models.Model`, it
runs on a separate `RDFAdminSite` with its own URL routes and form
generation, not through `django.contrib.admin.site.register()`.

Register a model in your app's `admin.py`:

```python
from djangordf.admin import rdf_admin_site, RDFModelAdmin
from myapp.models import Term


@rdf_admin_site.register(Term)
class TermAdmin(RDFModelAdmin):
    list_display = ("iri", "pref_label")
    fields = ("pref_label", "broader")
```

Mount the site in your project's URL conf:

```python
from django.urls import path
from djangordf.admin import rdf_admin_site

urlpatterns = [
    path("admin/rdf/", rdf_admin_site.urls),
    # ... rest of your project's URLs
]
```

The site then exposes a list view (`/admin/rdf/<Model>/`), add view
(`/admin/rdf/<Model>/add/`), change view
(`/admin/rdf/<Model>/<iri>/`), and delete confirmation
(`/admin/rdf/<Model>/<iri>/delete/`). Forms are auto-generated from
each model's declared properties (`DataProperty`, `LangStringProperty`,
`URIProperty`, `ObjectProperty`). `many=True` properties render as a
`Textarea` with one value per line; `LangStringProperty` uses the
`"value@lang"` shape; `ObjectProperty` takes the target IRI as text.

The site does **not** enforce authentication on its own — wrap its
URLs in your project's auth middleware or place them inside an
admin-only URL prefix.

## RDF schema migrations

`djangordf.schema` provides a Django-migrations-style framework for
evolving the RDF schema and data over time. Each change is a small
Python file under a configurable module
(`DJANGORDF_MIGRATIONS_MODULE`, default `rdf_migrations`); a
management command discovers and applies pending migrations in
dependency order; applied state lives in the triple store itself
under `urn:djangordf:migrations`.

Generate a blank template:

```bash
python manage.py makemigration_rdf rename_pref
# Created rdf_migrations/0001_rename_pref.py
```

Edit it:

```python
# rdf_migrations/0001_rename_pref.py
from rdflib import URIRef
from djangordf.schema import (
    Migration, RenamePredicate, CreateClass, AddPropertyDeclaration,
)


class Migration(Migration):
    name = "0001_rename_pref"
    dependencies = []
    operations = [
        CreateClass(
            URIRef("http://example.org/Book"),
            label="Book",
        ),
        AddPropertyDeclaration(
            URIRef("http://example.org/title"),
            kind="datatype",
            domain=URIRef("http://example.org/Book"),
        ),
        RenamePredicate(
            old=URIRef("http://example.org/oldTitle"),
            new=URIRef("http://example.org/title"),
        ),
    ]
```

Apply:

```bash
python manage.py migrate_rdf
# Applied 0001_rename_pref

python manage.py migrate_rdf --list
# Applied:
#   [X] 0001_rename_pref
# Pending:
#   (none)
```

Built-in operations:

- `RunSPARQL(sparql)` — escape hatch.
- `CreateClass(class_iri, label=, comment=)` — appends `owl:Class`
  to `DJANGORDF_ONTOLOGY_GRAPH` (default `urn:djangordf:ontology`).
- `DeleteClass(class_iri)` — strips every triple whose subject is
  that IRI from the ontology graph.
- `AddPropertyDeclaration(predicate, kind=, domain=, range=)` —
  declares the predicate (`kind="datatype"` or `"object"`) plus
  optional `rdfs:domain` / `rdfs:range`.
- `RenamePredicate(old, new, graph=)` — rewrites every
  `(?s, old, ?o)` triple to `(?s, new, ?o)`.

This first release is forward-only; rollback / `reverse()` paths
will land as a follow-up. Auto-diffing the current `RDFModel`
declarations into a migration is also out of scope —
`makemigration_rdf` writes a blank template that you fill in
manually.

## Reasoning

`djangordf.reasoning` materialises inferred triples into the backend.
Pick a reasoner via `settings.DJANGORDF_REASONER` (dotted import path)
or pass one to {func}`djangordf.reasoning.materialize`.

```python
from djangordf.reasoning import (
    CompositeReasoner, RDFSReasoner, SKOSReasoner, materialize,
)

# Run RDFS + SKOS rules in place over the default graph.
materialize(
    CompositeReasoner(RDFSReasoner(), SKOSReasoner()),
    source_graph="urn:djangordf:default",
)
```

Or via the management command, which honours
`DJANGORDF_REASONER`:

```python
DJANGORDF_REASONER = "djangordf.reasoning.SKOSReasoner"
```

```bash
python manage.py reason --source "urn:djangordf:default"
# Added 17 inferred triple(s).

python manage.py reason --dry-run
# [dry-run] Would add 17 inferred triple(s).
```

Built-in reasoners:

- `RDFSReasoner` — `subClassOf` transitivity and type propagation,
  `subPropertyOf` propagation, `domain` / `range` inference.
- `SKOSReasoner` — promotes `skos:broader` / `skos:narrower` to their
  transitive variants and closes those under transitivity; enforces
  `skos:exactMatch` symmetry.
- `CompositeReasoner(*reasoners)` — runs several reasoners inside one
  fixpoint envelope.
- `OWLRLReasoner` — optional wrapper around the third-party `owlrl`
  package (lazy-imported; raises a clear error if the package is not
  installed).

Each reasoner runs its rules in a fixpoint loop with a configurable
`max_iterations` budget. The default writes inferences back into the
source graph (in-place materialisation); pass `target_graph=` to keep
the source pristine.

## RDF schema migrations

`djangordf.schema` provides a Django-migrations-style framework for
evolving the RDF schema and data over time. Each change is a small
Python file under a configurable module
(`DJANGORDF_MIGRATIONS_MODULE`, default `rdf_migrations`); a
management command discovers and applies pending migrations in
dependency order; applied state lives in the triple store itself
under `urn:djangordf:migrations`.

Generate a blank template:

```bash
python manage.py makemigration_rdf rename_pref
# Created rdf_migrations/0001_rename_pref.py
```

Edit it:

```python
# rdf_migrations/0001_rename_pref.py
from rdflib import URIRef
from djangordf.schema import (
    Migration, RenamePredicate, CreateClass, AddPropertyDeclaration,
)


class Migration(Migration):
    name = "0001_rename_pref"
    dependencies = []
    operations = [
        CreateClass(
            URIRef("http://example.org/Book"),
            label="Book",
        ),
        AddPropertyDeclaration(
            URIRef("http://example.org/title"),
            kind="datatype",
            domain=URIRef("http://example.org/Book"),
        ),
        RenamePredicate(
            old=URIRef("http://example.org/oldTitle"),
            new=URIRef("http://example.org/title"),
        ),
    ]
```

Apply:

```bash
python manage.py migrate_rdf
# Applied 0001_rename_pref

python manage.py migrate_rdf --list
# Applied:
#   [X] 0001_rename_pref
# Pending:
#   (none)
```

Built-in operations:

- `RunSPARQL(sparql)` — escape hatch.
- `CreateClass(class_iri, label=, comment=)` — appends `owl:Class`
  to `DJANGORDF_ONTOLOGY_GRAPH` (default `urn:djangordf:ontology`).
- `DeleteClass(class_iri)` — strips every triple whose subject is
  that IRI from the ontology graph.
- `AddPropertyDeclaration(predicate, kind=, domain=, range=)` —
  declares the predicate (`kind="datatype"` or `"object"`) plus
  optional `rdfs:domain` / `rdfs:range`.
- `RenamePredicate(old, new, graph=)` — rewrites every
  `(?s, old, ?o)` triple to `(?s, new, ?o)`.

This first release is forward-only; rollback / `reverse()` paths
will land as a follow-up. Auto-diffing the current `RDFModel`
declarations into a migration is also out of scope — `makemigration_rdf`
writes a blank template that you fill in manually.
