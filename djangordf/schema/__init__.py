"""Django-style migrations for the RDF schema.

Define a ``Migration`` subclass per change, list ``operations`` from
:mod:`djangordf.schema.operations`, point at any ``dependencies`` by
migration name, and run ``python manage.py migrate_rdf`` to apply.

The applied-state recorder lives in the triple store itself
(``urn:djangordf:migrations``) so the next run knows what is already
in place.
"""
from .base import Migration
from .executor import Executor
from .operations import (
    AddPropertyDeclaration,
    CreateClass,
    DeleteClass,
    Operation,
    RenamePredicate,
    RunSPARQL,
)
from .recorder import MigrationRecorder


__all__ = [
    "AddPropertyDeclaration",
    "CreateClass",
    "DeleteClass",
    "Executor",
    "Migration",
    "MigrationRecorder",
    "Operation",
    "RenamePredicate",
    "RunSPARQL",
]
