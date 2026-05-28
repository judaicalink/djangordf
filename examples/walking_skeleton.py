#!/usr/bin/env python
"""Walking-skeleton acceptance script from spec §9.

Runs against the in-memory backend defined in ``tests/settings.py``;
no further changes to djangordf are required for this script to exit 0.
"""
import os
import sys

import django


def main() -> int:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    django.setup()

    from djangordf import LangStringProperty, ObjectProperty, RDFModel
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
    assert any(
        ls.lang == "en" and ls.value == "Book"
        for ls in buch.pref_label
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
