"""``python manage.py migrate_rdf`` — apply pending RDF migrations."""
from django.core.management.base import BaseCommand

from djangordf.schema import Executor


class Command(BaseCommand):
    help = "Apply pending djangordf migrations (see DJANGORDF_MIGRATIONS_MODULE)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--list",
            action="store_true",
            dest="list_only",
            help=(
                "Print applied and pending migrations without changing the "
                "store."
            ),
        )

    def handle(self, *args, **options):
        executor = Executor()
        if options.get("list_only"):
            applied, pending = executor.plan()
            self.stdout.write("Applied:")
            if applied:
                for m in applied:
                    self.stdout.write(f"  [X] {m.name}")
            else:
                self.stdout.write("  (none)")
            self.stdout.write("Pending:")
            if pending:
                for m in pending:
                    self.stdout.write(f"  [ ] {m.name}")
            else:
                self.stdout.write("  (none)")
            return

        newly_applied = executor.migrate()
        if not newly_applied:
            self.stdout.write("No migrations to apply.")
            return
        for migration in newly_applied:
            self.stdout.write(f"Applied {migration.name}")
