"""Tests for djangordf.backends.fuseki."""
from unittest import mock

import pytest
import requests
from rdflib import Literal, URIRef
from rdflib.namespace import XSD


def _mock_response(status=200, text="", content=None, content_type="text/plain"):
    response = mock.Mock()
    response.status_code = status
    response.text = text
    response.content = content if content is not None else text.encode("utf-8")
    response.headers = {"Content-Type": content_type}
    response.raise_for_status = mock.Mock()
    return response


# -- Constructor ------------------------------------------------------------


def test_construct_stores_endpoint():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    assert backend.endpoint == "http://example.org/sparql"


def test_endpoint_is_normalised_without_trailing_slash():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql/")
    assert backend.endpoint == "http://example.org/sparql"


def test_basic_auth_is_configured_on_session_when_credentials_given():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(
        endpoint="http://example.org/sparql",
        user="alice",
        password="secret",
    )
    assert backend.session.auth == ("alice", "secret")


def test_no_auth_when_credentials_missing():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    assert backend.session.auth is None


# -- query() ----------------------------------------------------------------


def test_construct_query_posts_to_query_endpoint_with_turtle_accept():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    turtle = (
        "<http://example.org/s> <http://example.org/p> "
        "<http://example.org/o> ."
    )
    with mock.patch.object(
        backend.session, "post",
        return_value=_mock_response(
            text=turtle, content_type="text/turtle",
        ),
    ) as post:
        result = backend.query("CONSTRUCT WHERE { ?s ?p ?o }")

    post.assert_called_once()
    args, kwargs = post.call_args
    assert args[0] == "http://example.org/sparql/query"
    assert kwargs["data"] == "CONSTRUCT WHERE { ?s ?p ?o }"
    assert kwargs["headers"]["Content-Type"] == "application/sparql-query"
    assert "text/turtle" in kwargs["headers"]["Accept"]
    assert (
        URIRef("http://example.org/s"),
        URIRef("http://example.org/p"),
        URIRef("http://example.org/o"),
    ) in result


def test_select_query_returns_parsed_result_bindings():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    json_body = (
        '{"head":{"vars":["o"]},'
        '"results":{"bindings":['
        '{"o":{"type":"literal","value":"hello"}}'
        "]}}"
    )
    with mock.patch.object(
        backend.session, "post",
        return_value=_mock_response(
            text=json_body, content=json_body.encode("utf-8"),
            content_type="application/sparql-results+json",
        ),
    ) as post:
        result = backend.query("SELECT ?o WHERE { ?s ?p ?o }")

    _, kwargs = post.call_args
    assert "application/sparql-results+json" in kwargs["headers"]["Accept"]
    rows = list(result)
    assert len(rows) == 1
    assert str(rows[0][0]) == "hello"


def test_ask_query_returns_boolean():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    json_body = '{"head":{},"boolean":true}'
    with mock.patch.object(
        backend.session, "post",
        return_value=_mock_response(
            text=json_body, content=json_body.encode("utf-8"),
            content_type="application/sparql-results+json",
        ),
    ):
        result = backend.query("ASK { ?s ?p ?o }")
    assert bool(result) is True


def test_query_type_detection_ignores_prefix_declarations():
    """A query with leading PREFIX lines still routes to CONSTRUCT handling."""
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    sparql = (
        "PREFIX ex: <http://example.org/>\n"
        "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"
    )
    with mock.patch.object(
        backend.session, "post",
        return_value=_mock_response(
            text="", content_type="text/turtle",
        ),
    ) as post:
        backend.query(sparql)
    _, kwargs = post.call_args
    assert "text/turtle" in kwargs["headers"]["Accept"]


def test_query_raises_on_http_error():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    bad = _mock_response(status=500, text="boom")
    bad.raise_for_status = mock.Mock(
        side_effect=requests.HTTPError("500")
    )
    with mock.patch.object(backend.session, "post", return_value=bad):
        with pytest.raises(requests.HTTPError):
            backend.query("SELECT ?s WHERE { ?s ?p ?o }")


# -- update() ---------------------------------------------------------------


def test_update_posts_to_update_endpoint_with_sparql_update_content_type():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    sparql = (
        'INSERT DATA { <http://example.org/s> <http://example.org/p> "v" }'
    )
    with mock.patch.object(
        backend.session, "post",
        return_value=_mock_response(),
    ) as post:
        backend.update(sparql)
    post.assert_called_once()
    args, kwargs = post.call_args
    assert args[0] == "http://example.org/sparql/update"
    assert kwargs["data"] == sparql
    assert kwargs["headers"]["Content-Type"] == "application/sparql-update"


def test_update_raises_on_http_error():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    bad = _mock_response(status=400, text="bad")
    bad.raise_for_status = mock.Mock(
        side_effect=requests.HTTPError("400")
    )
    with mock.patch.object(backend.session, "post", return_value=bad):
        with pytest.raises(requests.HTTPError):
            backend.update("CLEAR DEFAULT")


def test_update_returns_the_underlying_response():
    """Callers need access to the HTTP status / headers to tell e.g.
    200 from 204; the wrapper must forward the ``requests.Response``."""
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    response = _mock_response(status=204, text="")
    with mock.patch.object(
        backend.session, "post", return_value=response,
    ):
        result = backend.update("CLEAR DEFAULT")
    assert result is response
    assert result.status_code == 204


# -- add / remove / clear ---------------------------------------------------


def _capture_update(backend):
    """Patch update() to record the SPARQL string it would have sent."""
    captured = {}

    def fake_update(sparql):
        captured["sparql"] = sparql

    backend.update = fake_update
    return captured


def test_add_default_graph_emits_insert_data():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    captured = _capture_update(backend)
    backend.add(
        [(
            URIRef("http://example.org/s"),
            URIRef("http://example.org/p"),
            Literal("v"),
        )]
    )
    sparql = captured["sparql"]
    assert "INSERT DATA" in sparql
    assert "<http://example.org/s>" in sparql
    assert "<http://example.org/p>" in sparql
    assert '"v"' in sparql
    assert "GRAPH" not in sparql


def test_add_named_graph_wraps_triples_in_graph_block():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    captured = _capture_update(backend)
    g = URIRef("http://example.org/g")
    backend.add(
        [(
            URIRef("http://example.org/s"),
            URIRef("http://example.org/p"),
            Literal("v"),
        )],
        graph=g,
    )
    sparql = captured["sparql"]
    assert "INSERT DATA" in sparql
    assert "GRAPH <http://example.org/g>" in sparql


def test_add_serialises_typed_literals():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    captured = _capture_update(backend)
    backend.add(
        [(
            URIRef("http://example.org/s"),
            URIRef("http://example.org/p"),
            Literal(42, datatype=XSD.integer),
        )]
    )
    assert "42" in captured["sparql"]
    assert str(XSD.integer) in captured["sparql"]


def test_remove_with_full_triple_emits_delete_where():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    captured = _capture_update(backend)
    backend.remove(
        (
            URIRef("http://example.org/s"),
            URIRef("http://example.org/p"),
            Literal("v"),
        )
    )
    sparql = captured["sparql"]
    assert sparql.startswith("DELETE WHERE")
    assert "<http://example.org/s>" in sparql
    assert "<http://example.org/p>" in sparql


def test_remove_with_wildcards_uses_sparql_variables():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    captured = _capture_update(backend)
    backend.remove((URIRef("http://example.org/s"), None, None))
    sparql = captured["sparql"]
    assert "<http://example.org/s>" in sparql
    assert "?p" in sparql
    assert "?o" in sparql


def test_remove_in_named_graph_wraps_pattern_in_graph_block():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    captured = _capture_update(backend)
    backend.remove(
        (URIRef("http://example.org/s"), None, None),
        graph=URIRef("http://example.org/g"),
    )
    assert "GRAPH <http://example.org/g>" in captured["sparql"]


def test_clear_default_graph_emits_clear_default():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    captured = _capture_update(backend)
    backend.clear()
    assert captured["sparql"] == "CLEAR DEFAULT"


def test_clear_named_graph_emits_clear_silent_graph():
    from djangordf.backends.fuseki import FusekiBackend
    backend = FusekiBackend(endpoint="http://example.org/sparql")
    captured = _capture_update(backend)
    backend.clear(graph=URIRef("http://example.org/g"))
    assert captured["sparql"] == "CLEAR SILENT GRAPH <http://example.org/g>"
