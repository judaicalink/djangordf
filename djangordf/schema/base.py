"""The ``Migration`` base class.

Subclass it in a per-change file, list operations, and reference any
prior migrations by name through ``dependencies``::

    class Migration(Migration):
        name = "0002_rename_pref"
        dependencies = ["0001_initial"]
        operations = [
            RenamePredicate(
                old=URIRef("http://example.org/oldPred"),
                new=URIRef("http://example.org/newPred"),
            ),
        ]

The ``name`` field defaults to the module name if not set.
"""
from typing import List, Optional

from .operations import Operation


class Migration:
    """One forward-only RDF schema or data change."""

    name: Optional[str] = None
    dependencies: List[str] = []
    operations: List[Operation] = []

    def apply(self, backend) -> None:
        """Run every operation in declaration order against ``backend``."""
        for op in self.operations:
            op.apply(backend)
