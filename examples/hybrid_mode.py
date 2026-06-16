#!/usr/bin/env python
"""Hybrid mode example: link RDFModel triples to relational identifiers.

The pattern is to encode the relational primary key as a synthetic
IRI under a documented namespace (``urn:djangordf:user:<pk>``). Read
the IRI back as a `URIRef` and parse the pk out. No Django auth
tables are required for the round-trip — this example only relies on
the configured triple store backend.

For the inverse direction (a Django model storing the RDFModel IRI
of a concept it points at) use an ``URLField`` / ``TextField`` on the
relational side; no djangordf-specific code is needed.
"""
import os
import sys

import django


def main() -> int:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    django.setup()

    from rdflib import URIRef
    from djangordf import (
        LangStringProperty,
        RDFModel,
        URIProperty,
    )
    from djangordf.namespaces import LangString

    USER_NS = "urn:djangordf:user:"

    class Term(RDFModel):
        pref_label = LangStringProperty(many=True)
        created_by = URIProperty(
            predicate=URIRef("http://purl.org/dc/terms/creator"),
        )

    # Stand-in for a Django auth.User: we only need its pk for the
    # relational link. In a real project this would be
    # ``request.user.pk`` or similar.
    user_pk = 42
    user_iri = URIRef(f"{USER_NS}{user_pk}")

    term = Term.objects.create(
        pref_label=[LangString("Buch", "de")],
        created_by=user_iri,
    )

    reloaded = Term.objects.get(term.iri)
    assert reloaded.created_by == user_iri

    # Parse the relational pk back out of the synthetic IRI.
    recovered_pk = int(str(reloaded.created_by).removeprefix(USER_NS))
    assert recovered_pk == user_pk
    return 0


if __name__ == "__main__":
    sys.exit(main())
