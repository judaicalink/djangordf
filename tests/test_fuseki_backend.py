"""Tests for djangordf.backends.fuseki."""
from unittest import mock

import pytest
import requests
from rdflib import URIRef


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
