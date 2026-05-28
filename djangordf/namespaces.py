"""Namespace utilities for djangordf.

This milestone ships only ``LangString``. The full ``NamespaceRegistry``
with CURIE resolution and prefix bindings lands in issue #9.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class LangString:
    """A language-tagged literal, paired with a BCP 47 language tag.

    Used by ``LangStringProperty`` to round-trip ``rdf:langString``
    values cleanly between Python and the triple store.
    """

    value: str
    lang: str
