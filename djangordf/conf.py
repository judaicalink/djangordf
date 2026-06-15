"""Settings-driven configuration helpers for djangordf."""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from .backends.base import TripleStoreBackend
from .backends.memory import InMemoryBackend


_DEFAULT_BACKEND_CLASS = "djangordf.backends.memory.InMemoryBackend"

_BACKEND: TripleStoreBackend | None = None


def get_backend() -> TripleStoreBackend:
    """Return the process-wide triple-store backend instance.

    Reads ``settings.DJANGORDF_BACKEND``, expected to be a dict with at
    least a ``class`` key holding a dotted import path. Any other keys
    are forwarded as keyword arguments to the backend's constructor.
    Falls back to the in-memory backend if no setting is configured,
    so importing djangordf in a fresh Django project just works.

    The backend instance is cached at module level so that every
    ``RDFManager`` (one per ``RDFModel`` subclass) talks to the same
    triple store. This matters for cross-model reads — reverse
    lookups, for instance, dereference triples written by another
    model's manager. Tests should call :func:`reset_backend` between
    runs to release the cached instance.
    """
    global _BACKEND
    if _BACKEND is not None:
        return _BACKEND

    config = getattr(settings, "DJANGORDF_BACKEND", None)
    if config is None:
        _BACKEND = InMemoryBackend()
        return _BACKEND

    dotted = config.get("class", _DEFAULT_BACKEND_CLASS)
    try:
        backend_cls = import_string(dotted)
    except ImportError as exc:
        raise ImproperlyConfigured(
            f"DJANGORDF_BACKEND['class']={dotted!r} cannot be imported: {exc}"
        ) from exc

    kwargs = {k: v for k, v in config.items() if k != "class"}
    _BACKEND = backend_cls(**kwargs)
    return _BACKEND


def reset_backend() -> None:
    """Drop the cached backend instance so the next ``get_backend()``
    call builds a fresh one. Used between tests to ensure isolation.
    Also clears any ``_backend`` cached on existing ``RDFManager``
    instances declared during a previous test."""
    global _BACKEND
    _BACKEND = None
    from .models import _MODEL_REGISTRY
    for cls in _MODEL_REGISTRY.values():
        manager = getattr(cls, "objects", None)
        if manager is not None:
            manager._backend = None
