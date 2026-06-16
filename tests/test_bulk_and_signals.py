"""Tests for bulk operations and lifecycle signals."""
import pytest
from rdflib import URIRef
from rdflib.namespace import XSD


@pytest.fixture
def in_memory_backend(settings):
    settings.DJANGORDF_BACKEND = {
        "class": "djangordf.backends.memory.InMemoryBackend",
    }
    settings.DJANGORDF_DEFAULT_NAMESPACE = "http://example.org/d/"
    settings.DJANGORDF_DEFAULT_GRAPH = "http://example.org/g"


def _bulk_term_model(name):
    from djangordf import DataProperty, RDFModel
    return type(
        name,
        (RDFModel,),
        {
            "title": DataProperty(
                predicate=URIRef("http://example.org/title"),
            ),
            "count": DataProperty(
                predicate=URIRef("http://example.org/count"),
                datatype=XSD.integer,
            ),
        },
    )


# -- signals -----------------------------------------------------------------

def test_pre_and_post_save_fire_on_instance_save(in_memory_backend):
    from djangordf import post_save, pre_save
    Term = _bulk_term_model("SigSave")

    received = []

    def collector(sender, instance, signal, **kwargs):
        received.append((signal, sender, instance))

    pre_save.connect(collector, sender=Term)
    post_save.connect(collector, sender=Term)
    try:
        inst = Term.objects.create(title="x")
        assert len(received) == 2
        assert received[0][0] is pre_save
        assert received[1][0] is post_save
        assert received[0][1] is Term
        assert received[0][2] is inst
        assert received[1][2] is inst
    finally:
        pre_save.disconnect(collector, sender=Term)
        post_save.disconnect(collector, sender=Term)


def test_pre_and_post_delete_fire_on_instance_delete(in_memory_backend):
    from djangordf import post_delete, pre_delete
    Term = _bulk_term_model("SigDelete")

    received = []

    def collector(sender, instance, signal, **kwargs):
        received.append(signal)

    inst = Term.objects.create(title="x")
    pre_delete.connect(collector, sender=Term)
    post_delete.connect(collector, sender=Term)
    try:
        inst.delete()
        assert received == [pre_delete, post_delete]
    finally:
        pre_delete.disconnect(collector, sender=Term)
        post_delete.disconnect(collector, sender=Term)


def test_signals_are_importable_from_package_root():
    from djangordf import post_delete, post_save, pre_delete, pre_save
    from djangordf.signals import (
        post_delete as mod_post_delete,
        post_save as mod_post_save,
        pre_delete as mod_pre_delete,
        pre_save as mod_pre_save,
    )
    assert pre_save is mod_pre_save
    assert post_save is mod_post_save
    assert pre_delete is mod_pre_delete
    assert post_delete is mod_post_delete


# -- bulk_create -------------------------------------------------------------

def test_bulk_create_persists_every_instance(in_memory_backend):
    Term = _bulk_term_model("BulkCreatePersist")
    instances = [
        Term(title="A"),
        Term(title="B"),
        Term(title="C"),
    ]
    Term.objects.bulk_create(instances)
    titles = sorted(t.title for t in Term.objects.all())
    assert titles == ["A", "B", "C"]


def test_bulk_create_mints_iris_for_missing_ones(in_memory_backend):
    Term = _bulk_term_model("BulkCreateMint")
    instances = [Term(title="A"), Term(title="B")]
    Term.objects.bulk_create(instances)
    assert all(inst.iri is not None for inst in instances)
    assert all(
        str(inst.iri).startswith("http://example.org/d/") for inst in instances
    )


def test_bulk_create_issues_one_backend_update(in_memory_backend):
    from unittest import mock
    Term = _bulk_term_model("BulkCreateOneCall")
    manager = Term.objects
    with mock.patch.object(
        manager, "_backend", manager.backend,
    ):  # ensure cached
        with mock.patch.object(
            manager._backend, "update", wraps=manager._backend.update,
        ) as spy:
            manager.bulk_create([Term(title="A"), Term(title="B")])
    spy.assert_called_once()


def test_bulk_create_does_not_fire_signals(in_memory_backend):
    from djangordf import post_save, pre_save
    Term = _bulk_term_model("BulkCreateNoSig")
    received = []

    def collector(sender, instance, signal, **kwargs):
        received.append(signal)

    pre_save.connect(collector, sender=Term)
    post_save.connect(collector, sender=Term)
    try:
        Term.objects.bulk_create([Term(title="x"), Term(title="y")])
        assert received == []
    finally:
        pre_save.disconnect(collector, sender=Term)
        post_save.disconnect(collector, sender=Term)


def test_bulk_create_empty_list_is_noop(in_memory_backend):
    Term = _bulk_term_model("BulkCreateEmpty")
    result = Term.objects.bulk_create([])
    assert result == []


# -- bulk_update -------------------------------------------------------------

def test_bulk_update_overwrites_existing_instances(in_memory_backend):
    Term = _bulk_term_model("BulkUpdateApply")
    a = Term.objects.create(title="old-A")
    b = Term.objects.create(title="old-B")
    a.title = "new-A"
    b.title = "new-B"
    Term.objects.bulk_update([a, b])
    titles = sorted(t.title for t in Term.objects.all())
    assert titles == ["new-A", "new-B"]


def test_bulk_update_without_iri_raises(in_memory_backend):
    Term = _bulk_term_model("BulkUpdateBad")
    with pytest.raises(ValueError):
        Term.objects.bulk_update([Term(title="ghost")])


# -- bulk_delete -------------------------------------------------------------

def test_bulk_delete_strips_every_instance(in_memory_backend):
    Term = _bulk_term_model("BulkDeleteStrip")
    a = Term.objects.create(title="A")
    b = Term.objects.create(title="B")
    Term.objects.create(title="C")
    count = Term.objects.bulk_delete([a, b])
    assert count == 2
    titles = sorted(t.title for t in Term.objects.all())
    assert titles == ["C"]


def test_bulk_delete_does_not_fire_signals(in_memory_backend):
    from djangordf import post_delete, pre_delete
    Term = _bulk_term_model("BulkDeleteNoSig")
    a = Term.objects.create(title="A")
    b = Term.objects.create(title="B")
    received = []

    def collector(sender, instance, signal, **kwargs):
        received.append(signal)

    pre_delete.connect(collector, sender=Term)
    post_delete.connect(collector, sender=Term)
    try:
        Term.objects.bulk_delete([a, b])
        assert received == []
    finally:
        pre_delete.disconnect(collector, sender=Term)
        post_delete.disconnect(collector, sender=Term)


def test_bulk_delete_without_iri_raises(in_memory_backend):
    Term = _bulk_term_model("BulkDeleteBad")
    with pytest.raises(ValueError):
        Term.objects.bulk_delete([Term(title="ghost")])
