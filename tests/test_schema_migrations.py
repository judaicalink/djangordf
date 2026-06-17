"""Tests for ``djangordf.schema`` — operations, recorder, and executor.

The executor's filesystem discovery is exercised by writing fresh
migration modules into a temporary directory per test and tweaking
``sys.path`` so importlib can find them.
"""
import os
import sys
import textwrap

import pytest
from rdflib import URIRef


@pytest.fixture
def in_memory_backend(settings):
    settings.DJANGORDF_BACKEND = {
        "class": "djangordf.backends.memory.InMemoryBackend",
    }
    settings.DJANGORDF_DEFAULT_NAMESPACE = "http://example.org/d/"
    settings.DJANGORDF_DEFAULT_GRAPH = "http://example.org/g"


@pytest.fixture
def migration_module(tmp_path, monkeypatch):
    """Materialise a fresh package on disk, put it on sys.path, and
    return its dotted name. The package starts empty; tests write
    migration files into ``pkg_dir`` and the executor imports them."""
    pkg_name = "rdf_migrations_test_pkg"
    pkg_dir = tmp_path / pkg_name
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setitem(os.environ, "PYTHONDONTWRITEBYTECODE", "1")
    # Some prior tests may have imported the same package; drop the
    # cached entry so we can re-import the fresh tree.
    for module_name in list(sys.modules):
        if module_name == pkg_name or module_name.startswith(f"{pkg_name}."):
            sys.modules.pop(module_name)
    yield pkg_name, pkg_dir
    for module_name in list(sys.modules):
        if module_name == pkg_name or module_name.startswith(f"{pkg_name}."):
            sys.modules.pop(module_name)


def _write_migration(pkg_dir, filename, body):
    (pkg_dir / filename).write_text(textwrap.dedent(body))


# -- recorder --------------------------------------------------------------

def test_recorder_tracks_applied_and_pending(in_memory_backend):
    from djangordf import conf
    from djangordf.schema import MigrationRecorder

    backend = conf.get_backend()
    recorder = MigrationRecorder(backend)
    assert recorder.applied() == set()
    recorder.record("0001_a", when="2026-06-16T10:00:00+00:00")
    assert recorder.applied() == {"0001_a"}
    recorder.record("0002_b", when="2026-06-16T10:05:00+00:00")
    assert recorder.applied() == {"0001_a", "0002_b"}
    recorder.forget("0001_a")
    assert recorder.applied() == {"0002_b"}


# -- operations ------------------------------------------------------------

def test_run_sparql_executes_against_backend(in_memory_backend):
    from djangordf import conf
    from djangordf.schema import RunSPARQL

    backend = conf.get_backend()
    RunSPARQL(
        'INSERT DATA { GRAPH <urn:t> { '
        '<http://example.org/s> <http://example.org/p> "v" } }'
    ).apply(backend)
    g = backend.query(
        "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH <urn:t> { ?s ?p ?o } }"
    )
    assert len(g) == 1


def test_create_class_writes_owl_class_triple(in_memory_backend, settings):
    from djangordf import conf
    from djangordf.schema import CreateClass

    settings.DJANGORDF_ONTOLOGY_GRAPH = "urn:test:ontology"
    backend = conf.get_backend()
    cls_iri = URIRef("http://example.org/MyClass")
    CreateClass(cls_iri, label="My Class", comment="a docstring").apply(backend)

    g = backend.query(
        "CONSTRUCT { ?s ?p ?o } WHERE { "
        "GRAPH <urn:test:ontology> { ?s ?p ?o } }"
    )
    triples = list(g)
    assert (
        cls_iri,
        URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
        URIRef("http://www.w3.org/2002/07/owl#Class"),
    ) in triples


def test_delete_class_strips_triples(in_memory_backend, settings):
    from djangordf import conf
    from djangordf.schema import CreateClass, DeleteClass

    settings.DJANGORDF_ONTOLOGY_GRAPH = "urn:test:ontology"
    backend = conf.get_backend()
    cls_iri = URIRef("http://example.org/Doomed")
    CreateClass(cls_iri, label="goodbye").apply(backend)
    DeleteClass(cls_iri).apply(backend)

    g = backend.query(
        "CONSTRUCT { ?s ?p ?o } WHERE { "
        "GRAPH <urn:test:ontology> { ?s ?p ?o } }"
    )
    assert len(g) == 0


def test_add_property_declaration_datatype(in_memory_backend, settings):
    from djangordf import conf
    from djangordf.schema import AddPropertyDeclaration

    settings.DJANGORDF_ONTOLOGY_GRAPH = "urn:test:ontology"
    backend = conf.get_backend()
    pred = URIRef("http://example.org/title")
    AddPropertyDeclaration(
        pred,
        kind="datatype",
        domain="http://example.org/Term",
        range="http://www.w3.org/2001/XMLSchema#string",
    ).apply(backend)
    g = backend.query(
        "CONSTRUCT { ?s ?p ?o } WHERE { "
        "GRAPH <urn:test:ontology> { ?s ?p ?o } }"
    )
    triples = list(g)
    assert (
        pred,
        URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
        URIRef("http://www.w3.org/2002/07/owl#DatatypeProperty"),
    ) in triples
    assert (
        pred,
        URIRef("http://www.w3.org/2000/01/rdf-schema#domain"),
        URIRef("http://example.org/Term"),
    ) in triples


def test_add_property_declaration_object(in_memory_backend, settings):
    from djangordf import conf
    from djangordf.schema import AddPropertyDeclaration

    settings.DJANGORDF_ONTOLOGY_GRAPH = "urn:test:ontology"
    backend = conf.get_backend()
    pred = URIRef("http://example.org/related")
    AddPropertyDeclaration(pred, kind="object").apply(backend)
    g = backend.query(
        "CONSTRUCT { ?s ?p ?o } WHERE { "
        "GRAPH <urn:test:ontology> { ?s ?p ?o } }"
    )
    assert (
        pred,
        URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
        URIRef("http://www.w3.org/2002/07/owl#ObjectProperty"),
    ) in list(g)


def test_add_property_declaration_bad_kind_raises():
    from djangordf.schema import AddPropertyDeclaration
    with pytest.raises(ValueError):
        AddPropertyDeclaration("http://example.org/p", kind="bogus")


def test_rename_predicate_rewrites_existing_triples(in_memory_backend, settings):
    from djangordf import conf
    from djangordf.schema import RenamePredicate

    settings.DJANGORDF_DEFAULT_GRAPH = "urn:test:data"
    backend = conf.get_backend()
    old_pred = URIRef("http://example.org/oldName")
    new_pred = URIRef("http://example.org/newName")
    s = URIRef("http://example.org/s")
    backend.add([(s, old_pred, URIRef("http://example.org/o"))], graph="urn:test:data")

    RenamePredicate(old_pred, new_pred, graph="urn:test:data").apply(backend)

    g = backend.query(
        "CONSTRUCT { ?s ?p ?o } WHERE { "
        "GRAPH <urn:test:data> { ?s ?p ?o } }"
    )
    triples = list(g)
    assert (s, new_pred, URIRef("http://example.org/o")) in triples
    assert (s, old_pred, URIRef("http://example.org/o")) not in triples


# -- executor --------------------------------------------------------------

def test_executor_applies_pending_in_dependency_order(
    in_memory_backend, migration_module, settings,
):
    from djangordf import conf
    from djangordf.schema import Executor

    pkg_name, pkg_dir = migration_module
    _write_migration(pkg_dir, "0001_a.py", """
        from djangordf.schema import Migration, RunSPARQL


        class Migration(Migration):
            dependencies = []
            operations = [
                RunSPARQL(
                    'INSERT DATA { GRAPH <urn:m:t> { '
                    '<http://example.org/m1> <http://example.org/p> "1" } }'
                ),
            ]
    """)
    _write_migration(pkg_dir, "0002_b.py", """
        from djangordf.schema import Migration, RunSPARQL


        class Migration(Migration):
            dependencies = ["0001_a"]
            operations = [
                RunSPARQL(
                    'INSERT DATA { GRAPH <urn:m:t> { '
                    '<http://example.org/m2> <http://example.org/p> "2" } }'
                ),
            ]
    """)

    settings.DJANGORDF_MIGRATIONS_MODULE = pkg_name
    executor = Executor(backend=conf.get_backend())
    applied = executor.migrate()
    assert [m.name for m in applied] == ["0001_a", "0002_b"]

    # Idempotency: running again applies nothing.
    second_pass = executor.migrate()
    assert second_pass == []


def test_executor_plan_lists_applied_and_pending(
    in_memory_backend, migration_module, settings,
):
    from djangordf import conf
    from djangordf.schema import Executor, MigrationRecorder

    pkg_name, pkg_dir = migration_module
    _write_migration(pkg_dir, "0001_x.py", """
        from djangordf.schema import Migration
        class Migration(Migration):
            dependencies = []
            operations = []
    """)
    _write_migration(pkg_dir, "0002_y.py", """
        from djangordf.schema import Migration
        class Migration(Migration):
            dependencies = ["0001_x"]
            operations = []
    """)
    settings.DJANGORDF_MIGRATIONS_MODULE = pkg_name
    backend = conf.get_backend()
    MigrationRecorder(backend).record(
        "0001_x", when="2026-06-16T00:00:00+00:00",
    )

    applied, pending = Executor(backend=backend).plan()
    assert [m.name for m in applied] == ["0001_x"]
    assert [m.name for m in pending] == ["0002_y"]


def test_executor_unknown_dependency_raises(
    in_memory_backend, migration_module, settings,
):
    from django.core.exceptions import ImproperlyConfigured
    from djangordf.schema import Executor

    pkg_name, pkg_dir = migration_module
    _write_migration(pkg_dir, "0001_bad.py", """
        from djangordf.schema import Migration
        class Migration(Migration):
            dependencies = ["does-not-exist"]
            operations = []
    """)
    settings.DJANGORDF_MIGRATIONS_MODULE = pkg_name
    with pytest.raises(ImproperlyConfigured):
        Executor().plan()


def test_executor_cycle_raises(
    in_memory_backend, migration_module, settings,
):
    from django.core.exceptions import ImproperlyConfigured
    from djangordf.schema import Executor

    pkg_name, pkg_dir = migration_module
    _write_migration(pkg_dir, "0001_a.py", """
        from djangordf.schema import Migration
        class Migration(Migration):
            dependencies = ["0002_b"]
            operations = []
    """)
    _write_migration(pkg_dir, "0002_b.py", """
        from djangordf.schema import Migration
        class Migration(Migration):
            dependencies = ["0001_a"]
            operations = []
    """)
    settings.DJANGORDF_MIGRATIONS_MODULE = pkg_name
    with pytest.raises(ImproperlyConfigured):
        Executor().plan()


def test_executor_discover_returns_empty_when_module_missing(
    in_memory_backend, settings,
):
    from djangordf.schema import Executor

    settings.DJANGORDF_MIGRATIONS_MODULE = (
        "djangordf__nonexistent_package_for_test"
    )
    assert Executor().discover() == []


# -- management commands ---------------------------------------------------

def test_migrate_rdf_command_applies(
    in_memory_backend, migration_module, settings,
):
    from io import StringIO
    from django.core.management import call_command

    pkg_name, pkg_dir = migration_module
    _write_migration(pkg_dir, "0001_initial.py", """
        from djangordf.schema import Migration, RunSPARQL
        class Migration(Migration):
            dependencies = []
            operations = [
                RunSPARQL(
                    'INSERT DATA { GRAPH <urn:cmd:t> { '
                    '<http://example.org/x> <http://example.org/p> "1" } }'
                ),
            ]
    """)
    settings.DJANGORDF_MIGRATIONS_MODULE = pkg_name
    buf = StringIO()
    call_command("migrate_rdf", stdout=buf)
    assert "Applied 0001_initial" in buf.getvalue()


def test_migrate_rdf_command_list_only_does_not_mutate(
    in_memory_backend, migration_module, settings,
):
    from io import StringIO
    from django.core.management import call_command
    from djangordf import conf
    from djangordf.schema import MigrationRecorder

    pkg_name, pkg_dir = migration_module
    _write_migration(pkg_dir, "0001_check.py", """
        from djangordf.schema import Migration
        class Migration(Migration):
            dependencies = []
            operations = []
    """)
    settings.DJANGORDF_MIGRATIONS_MODULE = pkg_name
    buf = StringIO()
    call_command("migrate_rdf", "--list", stdout=buf)
    output = buf.getvalue()
    assert "0001_check" in output
    assert MigrationRecorder(conf.get_backend()).applied() == set()


def test_makemigration_rdf_command_writes_file(tmp_path):
    from django.core.management import call_command

    target = tmp_path / "rdf_migrations_made"
    call_command(
        "makemigration_rdf", "Add Buch Class",
        f"--dir={target}",
    )
    assert (target / "__init__.py").exists()
    files = sorted(p.name for p in target.iterdir() if p.suffix == ".py")
    files.remove("__init__.py")
    assert len(files) == 1
    assert files[0].startswith("0001_")
    body = (target / files[0]).read_text(encoding="utf-8")
    assert "class Migration(Migration):" in body


def test_makemigration_rdf_numbers_increment(tmp_path):
    from django.core.management import call_command

    target = tmp_path / "rdf_migrations_chain"
    call_command("makemigration_rdf", "first", f"--dir={target}")
    call_command("makemigration_rdf", "second", f"--dir={target}")
    files = sorted(
        p.name for p in target.iterdir()
        if p.suffix == ".py" and p.name != "__init__.py"
    )
    assert files[0].startswith("0001_")
    assert files[1].startswith("0002_")


# -- importable -----------------------------------------------------------

def test_schema_classes_are_importable():
    from djangordf.schema import (
        AddPropertyDeclaration,
        CreateClass,
        DeleteClass,
        Executor,
        Migration,
        MigrationRecorder,
        Operation,
        RenamePredicate,
        RunSPARQL,
    )
    for cls in (
        Migration, Operation, RunSPARQL, CreateClass, DeleteClass,
        AddPropertyDeclaration, RenamePredicate,
        MigrationRecorder, Executor,
    ):
        assert callable(cls)
