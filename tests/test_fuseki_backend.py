"""Tests for djangordf.backends.fuseki."""


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
