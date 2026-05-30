"""Tests for ``python manage.py dump_ontology``."""
from io import StringIO

from django.core.management import call_command
from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF


def test_command_writes_turtle_to_stdout():
    from djangordf import DataProperty, RDFModel

    class CmdTermA(RDFModel):
        title = DataProperty(predicate=URIRef("http://example.org/title-a"))

    buf = StringIO()
    call_command("dump_ontology", stdout=buf)
    output = buf.getvalue()
    assert output.strip(), "expected non-empty turtle output"

    parsed = Graph()
    parsed.parse(data=output, format="turtle")
    assert (CmdTermA._meta.class_iri, RDF.type, OWL.Class) in parsed


def test_command_writes_to_output_file(tmp_path):
    from djangordf import DataProperty, RDFModel

    class CmdTermB(RDFModel):
        title = DataProperty(predicate=URIRef("http://example.org/title-b"))

    out = tmp_path / "ontology.ttl"
    call_command("dump_ontology", output=str(out))
    assert out.exists()
    data = out.read_text(encoding="utf-8")

    parsed = Graph()
    parsed.parse(data=data, format="turtle")
    assert (CmdTermB._meta.class_iri, RDF.type, OWL.Class) in parsed


def test_command_respects_format_xml():
    from djangordf import DataProperty, RDFModel

    class CmdTermC(RDFModel):
        title = DataProperty(predicate=URIRef("http://example.org/title-c"))

    buf = StringIO()
    call_command("dump_ontology", format="xml", stdout=buf)
    output = buf.getvalue()
    assert "<rdf:RDF" in output or "<RDF" in output

    parsed = Graph()
    parsed.parse(data=output, format="xml")
    assert (CmdTermC._meta.class_iri, RDF.type, OWL.Class) in parsed
