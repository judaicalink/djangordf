"""``python manage.py reason`` — materialise inferred triples.

Resolves the reasoner from ``--reasoner`` or ``settings.DJANGORDF_REASONER``,
runs it over the configured source / target graphs, and reports the
number of newly-inferred triples.
"""
from django.core.management.base import BaseCommand, CommandError

from djangordf.reasoning import materialize


class Command(BaseCommand):
    help = (
        "Materialise inferred triples into the configured backend. "
        "Picks a reasoner from --reasoner or DJANGORDF_REASONER."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reasoner",
            default=None,
            help=(
                "Dotted import path of a Reasoner class "
                "(e.g. djangordf.reasoning.RDFSReasoner). Overrides "
                "DJANGORDF_REASONER."
            ),
        )
        parser.add_argument(
            "--source",
            default=None,
            help="Source graph IRI (default: urn:djangordf:default).",
        )
        parser.add_argument(
            "--target",
            default=None,
            help="Target graph IRI (default: same as --source).",
        )
        parser.add_argument(
            "--max-iterations",
            type=int,
            default=50,
            help="Maximum fixpoint iterations (default: 50).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help=(
                "Run reasoning into a scratch graph and report the count "
                "without changing the configured target."
            ),
        )

    def handle(self, *args, **options):
        try:
            kwargs = {
                "source_graph": options.get("source"),
                "target_graph": options.get("target"),
                "max_iterations": options.get("max_iterations"),
            }
            if options.get("dry_run"):
                scratch = "urn:djangordf:reasoning:scratch"
                kwargs["target_graph"] = scratch
                # Use the source as-is, but write inferences into the
                # scratch graph so the configured target stays untouched.
                count = materialize(
                    reasoner=options.get("reasoner"),
                    **kwargs,
                )
                self.stdout.write(
                    f"[dry-run] Would add {count} inferred triple(s)."
                )
                # Wipe the scratch graph.
                from djangordf.conf import get_backend
                backend = get_backend()
                backend.update(f"CLEAR SILENT GRAPH <{scratch}>")
            else:
                count = materialize(
                    reasoner=options.get("reasoner"),
                    **kwargs,
                )
                self.stdout.write(
                    f"Added {count} inferred triple(s)."
                )
        except Exception as exc:
            raise CommandError(str(exc))
