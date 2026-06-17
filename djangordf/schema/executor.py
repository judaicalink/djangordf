"""Discover, sort and apply RDF migrations."""
import importlib
import inspect
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Tuple

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from ..conf import get_backend
from .base import Migration
from .recorder import MigrationRecorder


_DEFAULT_MODULE = "rdf_migrations"


def _migrations_module_path() -> str:
    try:
        configured = getattr(settings, "DJANGORDF_MIGRATIONS_MODULE", None)
    except ImproperlyConfigured:
        configured = None
    return configured or _DEFAULT_MODULE


class Executor:
    """Discover ``Migration`` subclasses, sort them topologically, and
    apply any that the recorder has not seen yet."""

    def __init__(self, backend=None, module_path: Optional[str] = None):
        self.backend = backend if backend is not None else get_backend()
        self.module_path = module_path or _migrations_module_path()
        self.recorder = MigrationRecorder(self.backend)

    # -- discovery ---------------------------------------------------------

    def discover(self) -> List[Migration]:
        """Import every ``*.py`` under the configured module, collect
        ``Migration`` subclasses, and return one instance per class
        sorted lexically by name."""
        try:
            pkg = importlib.import_module(self.module_path)
        except ModuleNotFoundError:
            return []
        # The package's filesystem path.
        pkg_file = getattr(pkg, "__file__", None)
        if pkg_file is None or not pkg_file.endswith("__init__.py"):
            return []
        pkg_dir = os.path.dirname(pkg_file)
        names = sorted(
            os.path.splitext(name)[0]
            for name in os.listdir(pkg_dir)
            if name.endswith(".py") and name != "__init__.py"
        )
        migrations: List[Migration] = []
        for module_name in names:
            full = f"{self.module_path}.{module_name}"
            module = importlib.import_module(full)
            for attr_name, attr in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(attr, Migration)
                    and attr is not Migration
                    and attr.__module__ == full
                ):
                    instance = attr()
                    if instance.name is None:
                        instance.name = module_name
                    migrations.append(instance)
        return migrations

    # -- sorting -----------------------------------------------------------

    def _topo_sort(
        self,
        migrations: Sequence[Migration],
    ) -> List[Migration]:
        """Kahn-style topological sort by ``dependencies``."""
        by_name: Dict[str, Migration] = {m.name: m for m in migrations}
        for m in migrations:
            for dep in m.dependencies:
                if dep not in by_name:
                    raise ImproperlyConfigured(
                        f"Migration {m.name!r} depends on unknown "
                        f"migration {dep!r}"
                    )
        in_degree = {m.name: 0 for m in migrations}
        edges: Dict[str, List[str]] = {m.name: [] for m in migrations}
        for m in migrations:
            for dep in m.dependencies:
                edges[dep].append(m.name)
                in_degree[m.name] += 1
        # Stable ordering: pick the alphabetically smallest ready name.
        ordered: List[Migration] = []
        ready = sorted([n for n, d in in_degree.items() if d == 0])
        while ready:
            name = ready.pop(0)
            ordered.append(by_name[name])
            for downstream in edges[name]:
                in_degree[downstream] -= 1
                if in_degree[downstream] == 0:
                    ready.append(downstream)
            ready.sort()
        if len(ordered) != len(migrations):
            unresolved = {
                m.name for m in migrations
                if m not in ordered
            }
            raise ImproperlyConfigured(
                f"Cyclic dependency in RDF migrations: {sorted(unresolved)!r}"
            )
        return ordered

    # -- plan + apply ------------------------------------------------------

    def plan(self) -> Tuple[List[Migration], List[Migration]]:
        """Return ``(applied, pending)`` lists in execution order."""
        all_sorted = self._topo_sort(self.discover())
        applied_names = self.recorder.applied()
        applied = [m for m in all_sorted if m.name in applied_names]
        pending = [m for m in all_sorted if m.name not in applied_names]
        return applied, pending

    def migrate(self) -> List[Migration]:
        """Apply every pending migration in dependency order and
        return the list of newly-applied migrations."""
        _, pending = self.plan()
        when = datetime.now(tz=timezone.utc).isoformat()
        for migration in pending:
            migration.apply(self.backend)
            self.recorder.record(migration.name, when=when)
        return pending
