"""Tests for djangordf.loaders — external SKOS vocabulary ingestion."""
from unittest import mock

import pytest
from rdflib import Graph, Literal, URIRef


_SAMPLE_TURTLE = (
    "@prefix ex: <http://example.org/> .\n"
    "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n"
    "ex:buch a skos:Concept ;\n"
    '    skos:prefLabel "Buch"@de , "Book"@en .\n'
)


@pytest.fixture
def in_memory_backend(settings):
    """Configure the in-memory backend so the loader writes through to
    the same store every test inspects."""
    settings.DJANGORDF_BACKEND = {
        "class": "djangordf.backends.memory.InMemoryBackend",
    }
    settings.DJANGORDF_DEFAULT_NAMESPACE = "http://example.org/d/"
    settings.DJANGORDF_DEFAULT_GRAPH = "http://example.org/g"


def _read_graph(backend, graph_iri):
    return backend.query(
        "CONSTRUCT { ?s ?p ?o } WHERE { "
        f"GRAPH <{graph_iri}> {{ ?s ?p ?o }} }}"
    )


def test_load_skos_from_filesystem(in_memory_backend, tmp_path):
    from djangordf import conf, load_skos

    f = tmp_path / "vocab.ttl"
    f.write_text(_SAMPLE_TURTLE, encoding="utf-8")

    n = load_skos(str(f))
    backend = conf.get_backend()
    g = _read_graph(backend, "urn:djangordf:external")
    assert n == 3
    assert (
        URIRef("http://example.org/buch"),
        URIRef("http://www.w3.org/2004/02/skos/core#prefLabel"),
        Literal("Buch", lang="de"),
    ) in g


def test_load_skos_from_rdflib_graph(in_memory_backend):
    from djangordf import conf, load_skos

    g = Graph()
    g.parse(data=_SAMPLE_TURTLE, format="turtle")

    n = load_skos(g)
    backend = conf.get_backend()
    stored = _read_graph(backend, "urn:djangordf:external")
    assert n == 3
    assert len(stored) == 3


def test_load_skos_explicit_graph_override(in_memory_backend, tmp_path):
    from djangordf import conf, load_skos

    f = tmp_path / "vocab.ttl"
    f.write_text(_SAMPLE_TURTLE, encoding="utf-8")

    load_skos(str(f), graph="http://example.org/imported")
    backend = conf.get_backend()
    in_target = _read_graph(backend, "http://example.org/imported")
    in_default = _read_graph(backend, "urn:djangordf:external")
    assert len(in_target) == 3
    assert len(in_default) == 0


def test_load_skos_respects_external_graph_setting(
    in_memory_backend, settings, tmp_path,
):
    settings.DJANGORDF_EXTERNAL_GRAPH = "http://example.org/imports"
    from djangordf import conf, load_skos

    f = tmp_path / "vocab.ttl"
    f.write_text(_SAMPLE_TURTLE, encoding="utf-8")

    load_skos(str(f))
    backend = conf.get_backend()
    stored = _read_graph(backend, "http://example.org/imports")
    assert len(stored) == 3


def test_load_skos_format_override_when_extension_misleads(
    in_memory_backend, tmp_path,
):
    from djangordf import conf, load_skos

    # Write turtle content into a file with a misleading extension.
    f = tmp_path / "vocab.bin"
    f.write_text(_SAMPLE_TURTLE, encoding="utf-8")

    n = load_skos(str(f), format="turtle")
    backend = conf.get_backend()
    stored = _read_graph(backend, "urn:djangordf:external")
    assert n == 3
    assert len(stored) == 3


def test_load_skos_from_http_url_uses_accept_header(in_memory_backend):
    from djangordf import conf, load_skos

    fake_response = mock.Mock()
    fake_response.text = _SAMPLE_TURTLE
    fake_response.headers = {"Content-Type": "text/turtle; charset=utf-8"}
    fake_response.raise_for_status = mock.Mock()

    with mock.patch(
        "djangordf.loaders.requests.get", return_value=fake_response,
    ) as fake_get:
        n = load_skos("https://example.org/skos/buch.ttl")

    assert n == 3
    fake_get.assert_called_once()
    args, kwargs = fake_get.call_args
    assert args[0] == "https://example.org/skos/buch.ttl"
    accept = kwargs["headers"]["Accept"]
    assert "text/turtle" in accept
    assert "application/rdf+xml" in accept

    backend = conf.get_backend()
    stored = _read_graph(backend, "urn:djangordf:external")
    assert len(stored) == 3


def test_load_skos_http_format_from_content_type(in_memory_backend):
    from djangordf import load_skos

    fake_response = mock.Mock()
    fake_response.text = _SAMPLE_TURTLE
    fake_response.headers = {"Content-Type": "text/turtle"}
    fake_response.raise_for_status = mock.Mock()

    with mock.patch(
        "djangordf.loaders.requests.get", return_value=fake_response,
    ):
        n = load_skos("https://example.org/no-extension-here")
    assert n == 3


def test_load_skos_raises_on_unsupported_source_type(in_memory_backend):
    from djangordf import load_skos

    with pytest.raises(TypeError):
        load_skos(42)


def test_load_skos_passes_explicit_backend(in_memory_backend, tmp_path):
    from djangordf import load_skos
    from djangordf.backends.memory import InMemoryBackend

    explicit = InMemoryBackend()
    f = tmp_path / "vocab.ttl"
    f.write_text(_SAMPLE_TURTLE, encoding="utf-8")

    n = load_skos(str(f), backend=explicit)
    stored = _read_graph(explicit, "urn:djangordf:external")
    assert n == 3
    assert len(stored) == 3


def test_load_external_concept_dereferences_iri(in_memory_backend):
    from djangordf import load_external_concept

    fake_response = mock.Mock()
    fake_response.text = _SAMPLE_TURTLE
    fake_response.headers = {"Content-Type": "text/turtle"}
    fake_response.raise_for_status = mock.Mock()

    with mock.patch(
        "djangordf.loaders.requests.get", return_value=fake_response,
    ) as fake_get:
        n = load_external_concept(URIRef("https://d-nb.info/gnd/4001577-9"))

    assert n == 3
    args, _ = fake_get.call_args
    assert args[0] == "https://d-nb.info/gnd/4001577-9"


def test_load_skos_loaders_importable_from_package_root():
    from djangordf import load_skos as top_skos
    from djangordf import load_external_concept as top_concept
    from djangordf.loaders import (
        load_skos as mod_skos,
        load_external_concept as mod_concept,
    )
    assert top_skos is mod_skos
    assert top_concept is mod_concept
