"""``python manage.py makemigration_rdf <name>`` — write a blank migration template."""
import importlib
import os
import re

from django.conf import settings
from django.core.management.base import BaseCommand


_DEFAULT_MODULE = "rdf_migrations"


_TEMPLATE = '''"""Auto-generated migration template. Fill in ``operations`` and
list any prior migrations under ``dependencies`` before running
``python manage.py migrate_rdf``."""
from djangordf.schema import Migration


class Migration(Migration):
    name = "{name}"
    dependencies = []
    operations = []
'''


def _slugify(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", text)
    return cleaned.strip("_") or "migration"


class Command(BaseCommand):
    help = (
        "Write a blank djangordf migration template into the configured "
        "migrations module (see DJANGORDF_MIGRATIONS_MODULE)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "name",
            help="Short descriptive name for the migration (e.g. 'rename_pref').",
        )
        parser.add_argument(
            "--dir",
            dest="output_dir",
            default=None,
            help=(
                "Override the target directory. Defaults to the resolved "
                "filesystem path of DJANGORDF_MIGRATIONS_MODULE; falls "
                "back to './rdf_migrations/' relative to the project."
            ),
        )

    def handle(self, *args, name, output_dir, **options):
        target_dir = output_dir or self._default_target_dir()
        os.makedirs(target_dir, exist_ok=True)
        init_path = os.path.join(target_dir, "__init__.py")
        if not os.path.exists(init_path):
            with open(init_path, "w", encoding="utf-8") as fp:
                fp.write("")

        slug = _slugify(name)
        next_number = self._next_number(target_dir)
        prefix = f"{next_number:04d}"
        migration_name = f"{prefix}_{slug}"
        file_path = os.path.join(target_dir, f"{migration_name}.py")
        with open(file_path, "w", encoding="utf-8") as fp:
            fp.write(_TEMPLATE.format(name=migration_name))
        self.stdout.write(f"Created {file_path}")

    def _default_target_dir(self) -> str:
        module_path = getattr(
            settings, "DJANGORDF_MIGRATIONS_MODULE", _DEFAULT_MODULE,
        )
        try:
            module = importlib.import_module(module_path)
            module_file = getattr(module, "__file__", None)
            if module_file and module_file.endswith("__init__.py"):
                return os.path.dirname(module_file)
        except ModuleNotFoundError:
            pass
        base_dir = self._project_base_dir()
        candidate = os.path.join(base_dir, *module_path.split("."))
        return candidate

    def _project_base_dir(self) -> str:
        base_dir = getattr(settings, "BASE_DIR", None)
        if base_dir is not None:
            return str(base_dir)
        return os.getcwd()

    def _next_number(self, target_dir: str) -> int:
        existing = []
        if os.path.isdir(target_dir):
            for fn in os.listdir(target_dir):
                m = re.match(r"^(\d{4})_", fn)
                if m:
                    existing.append(int(m.group(1)))
        return (max(existing) if existing else 0) + 1
