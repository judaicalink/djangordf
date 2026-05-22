"""Triple-store backend abstraction for djangordf."""
from .base import TripleStoreBackend
from .memory import InMemoryBackend

__all__ = ["TripleStoreBackend", "InMemoryBackend"]
