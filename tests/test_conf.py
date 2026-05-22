"""Tests for djangordf.conf."""
import pytest
from django.core.exceptions import ImproperlyConfigured

from djangordf.backends.base import TripleStoreBackend
from djangordf.backends.memory import InMemoryBackend


class RecordingBackend(TripleStoreBackend):
    """Helper backend that records constructor kwargs for inspection."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def query(self, sparql):
        return None

    def update(self, sparql):
        return None

    def add(self, triples, graph=None):
        return None

    def remove(self, pattern, graph=None):
        return None

    def clear(self, graph=None):
        return None


def test_get_backend_returns_in_memory_by_default(settings):
    """With no DJANGORDF_BACKEND configured, the factory must fall
    back to the in-memory backend so a quickstart works without any
    Django configuration."""
    if hasattr(settings, "DJANGORDF_BACKEND"):
        del settings.DJANGORDF_BACKEND
    from djangordf.conf import get_backend
    backend = get_backend()
    assert isinstance(backend, InMemoryBackend)


def test_get_backend_resolves_dotted_class_path(settings):
    settings.DJANGORDF_BACKEND = {
        "class": "djangordf.backends.memory.InMemoryBackend",
    }
    from djangordf.conf import get_backend
    backend = get_backend()
    assert isinstance(backend, InMemoryBackend)


def test_get_backend_passes_extra_kwargs_to_backend(settings):
    """Settings keys other than ``class`` are forwarded as kwargs."""
    settings.DJANGORDF_BACKEND = {
        "class": "tests.test_conf.RecordingBackend",
        "endpoint": "http://example.org/sparql",
        "user": "alice",
    }
    from djangordf.conf import get_backend
    backend = get_backend()
    assert backend.kwargs == {
        "endpoint": "http://example.org/sparql",
        "user": "alice",
    }


def test_get_backend_raises_for_bad_dotted_path(settings):
    settings.DJANGORDF_BACKEND = {"class": "no.such.module.Class"}
    from djangordf.conf import get_backend
    with pytest.raises(ImproperlyConfigured):
        get_backend()
