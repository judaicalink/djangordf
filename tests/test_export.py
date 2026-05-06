"""Tests for djangordf.functions.export_model_to_rdf."""
import datetime
import logging
import os

import pytest
from rdflib import Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from djangordf import export_model_to_rdf
from tests.conftest import load_graph
from tests.models import SampleModel

pytestmark = pytest.mark.django_db


DEFAULT_NS = Namespace("http://example.org/samplemodel/")


def _subject_for(instance, ns=DEFAULT_NS):
    return URIRef(ns[str(instance.pk)])


def test_writes_turtle_file_to_output_dir(tmp_path):
    SampleModel.objects.create(name="alpha")

    out = export_model_to_rdf(
        SampleModel, "smoke", output_dir=str(tmp_path),
    )

    assert os.path.isfile(out)
    assert out.startswith(str(tmp_path))
    assert out.endswith(".ttl")


def test_default_namespace_emits_rdf_type(tmp_path):
    inst = SampleModel.objects.create(name="alpha")

    out = export_model_to_rdf(
        SampleModel, "ns_default", output_dir=str(tmp_path),
    )

    g = load_graph(out)
    s = _subject_for(inst)
    assert (s, RDF.type, URIRef(DEFAULT_NS["SampleModel"])) in g


def test_custom_namespace_used_for_subjects_and_class(tmp_path):
    inst = SampleModel.objects.create(name="alpha")
    custom = "http://judaicalink.org/sample/"

    out = export_model_to_rdf(
        SampleModel,
        "ns_custom",
        namespace=custom,
        output_dir=str(tmp_path),
    )

    g = load_graph(out)
    s = URIRef(custom + str(inst.pk))
    assert (s, RDF.type, URIRef(custom + "SampleModel")) in g


def test_bool_field_is_xsd_boolean(tmp_path):
    """Regression: bool used to serialise as xsd:integer because bool is
    a subclass of int in Python."""
    inst = SampleModel.objects.create(name="alpha", is_active=True)

    out = export_model_to_rdf(
        SampleModel, "bool_test", output_dir=str(tmp_path),
    )

    g = load_graph(out)
    s = _subject_for(inst)
    p = URIRef(DEFAULT_NS["is_active"])
    assert (s, p, Literal(True, datatype=XSD.boolean)) in g
    # And explicitly NOT xsd:integer for the same predicate.
    assert (s, p, Literal(1, datatype=XSD.integer)) not in g


def test_int_field_is_xsd_integer(tmp_path):
    inst = SampleModel.objects.create(name="alpha", count=42)

    out = export_model_to_rdf(
        SampleModel, "int_test", output_dir=str(tmp_path),
    )

    g = load_graph(out)
    s = _subject_for(inst)
    p = URIRef(DEFAULT_NS["count"])
    assert (s, p, Literal(42, datatype=XSD.integer)) in g


def test_float_field_is_xsd_float(tmp_path):
    inst = SampleModel.objects.create(name="alpha", ratio=1.5)

    out = export_model_to_rdf(
        SampleModel, "float_test", output_dir=str(tmp_path),
    )

    g = load_graph(out)
    s = _subject_for(inst)
    p = URIRef(DEFAULT_NS["ratio"])
    assert (s, p, Literal(1.5, datatype=XSD.float)) in g


def test_string_field_is_xsd_string(tmp_path):
    inst = SampleModel.objects.create(name="alpha")

    out = export_model_to_rdf(
        SampleModel, "str_test", output_dir=str(tmp_path),
    )

    g = load_graph(out)
    s = _subject_for(inst)
    p = URIRef(DEFAULT_NS["name"])
    assert (s, p, Literal("alpha", datatype=XSD.string)) in g


def test_datetime_field_is_iso_xsd_datetime(tmp_path):
    when = datetime.datetime(
        2026, 1, 15, 12, 30, 45, tzinfo=datetime.timezone.utc,
    )
    inst = SampleModel.objects.create(name="alpha", created_at=when)
    inst.refresh_from_db()

    out = export_model_to_rdf(
        SampleModel, "dt_test", output_dir=str(tmp_path),
    )

    g = load_graph(out)
    s = _subject_for(inst)
    p = URIRef(DEFAULT_NS["created_at"])
    assert (
        s,
        p,
        Literal(inst.created_at.isoformat(), datatype=XSD.dateTime),
    ) in g


def test_none_field_values_are_skipped(tmp_path):
    inst = SampleModel.objects.create(
        name="alpha", created_at=None, note=None,
    )

    out = export_model_to_rdf(
        SampleModel, "none_test", output_dir=str(tmp_path),
    )

    g = load_graph(out)
    s = _subject_for(inst)
    assert list(g.triples((s, URIRef(DEFAULT_NS["created_at"]), None))) == []
    assert list(g.triples((s, URIRef(DEFAULT_NS["note"]), None))) == []


def test_dump_metadata_uses_class_iri_not_string_literal(tmp_path):
    """Regression: the dump-metadata resource used to be typed with a
    string literal on rdf:type, which is invalid RDF."""
    SampleModel.objects.create(name="alpha")

    out = export_model_to_rdf(
        SampleModel, "mymeta", output_dir=str(tmp_path),
    )

    g = load_graph(out)
    meta = URIRef(DEFAULT_NS["dump_metadata"])
    klass = URIRef(DEFAULT_NS["DumpMetadata"])
    assert (meta, RDF.type, klass) in g
    assert (
        meta,
        URIRef(DEFAULT_NS["dump_name"]),
        Literal("mymeta", datatype=XSD.string),
    ) in g


def test_unsupported_field_type_logs_warning(tmp_path, caplog):
    """BinaryField returns bytes, which the exporter cannot map to any
    XSD type — it must log a warning instead of silently dropping it."""
    SampleModel.objects.create(name="alpha", data=b"\x00\x01\x02")

    with caplog.at_level(logging.WARNING, logger="djangordf.functions"):
        export_model_to_rdf(
            SampleModel, "warn_test", output_dir=str(tmp_path),
        )

    messages = [r.getMessage() for r in caplog.records]
    assert any("Unhandled field type" in m for m in messages)
    assert any("data" in m for m in messages)
