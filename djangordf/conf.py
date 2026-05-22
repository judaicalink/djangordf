"""Settings-driven configuration helpers for djangordf."""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from .backends.base import TripleStoreBackend
from .backends.memory import InMemoryBackend


_DEFAULT_BACKEND_CLASS = "djangordf.backends.memory.InMemoryBackend"


def get_backend() -> TripleStoreBackend:
    """Build a triple-store backend instance from Django settings.

    Reads ``settings.DJANGORDF_BACKEND``, expected to be a dict with at
    least a ``class`` key holding a dotted import path. Any other keys
    are forwarded as keyword arguments to the backend's constructor.
    Falls back to the in-memory backend if no setting is configured,
    so importing djangordf in a fresh Django project just works.
    """
    config = getattr(settings, "DJANGORDF_BACKEND", None)
    if config is None:
        return InMemoryBackend()

    dotted = config.get("class", _DEFAULT_BACKEND_CLASS)
    try:
        backend_cls = import_string(dotted)
    except ImportError as exc:
        raise ImproperlyConfigured(
            f"DJANGORDF_BACKEND['class']={dotted!r} cannot be imported: {exc}"
        ) from exc

    kwargs = {k: v for k, v in config.items() if k != "class"}
    return backend_cls(**kwargs)
