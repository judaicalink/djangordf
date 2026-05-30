"""``python manage.py dump_ontology`` — write the model-derived OWL ontology to stdout or a file."""
from django.core.management.base import BaseCommand

from djangordf.ontology import generate_ontology


_FORMAT_CHOICES = ("turtle", "xml", "json-ld", "n3")


class Command(BaseCommand):
    help = (
        "Generate an OWL ontology from the declared RDFModel classes "
        "and write it to stdout or a file."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            "-o",
            default="-",
            help="Output file path. Use '-' for stdout (default).",
        )
        parser.add_argument(
            "--format",
            "-f",
            default="turtle",
            choices=_FORMAT_CHOICES,
            help="Serialisation format (default: turtle).",
        )

    def handle(self, *args, **options):
        graph = generate_ontology()
        data = graph.serialize(format=options["format"])

        output = options["output"]
        if output == "-":
            self.stdout.write(data)
            return
        with open(output, "w", encoding="utf-8") as fp:
            fp.write(data)
