"""RDF export utilities for Django models."""
import logging
import os
from datetime import datetime

from django.conf import settings
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import XSD

logger = logging.getLogger(__name__)


def export_model_to_rdf(model, dump_name, namespace=None, output_dir=None):
    """Export all instances of a Django model to a Turtle RDF file.

    Each instance becomes a subject identified by its primary key. Each
    model field becomes a predicate; values are emitted as typed literals.

    :param model: Django model class to export.
    :param dump_name: Logical name used in the file name and dump metadata.
    :param namespace: Optional base IRI. Defaults to
        ``http://example.org/<modelname>/``.
    :param output_dir: Directory the Turtle file is written to. Defaults
        to ``settings.BASE_DIR``.
    :returns: Absolute path of the written Turtle file.
    """
    ns_uri = namespace or f"http://example.org/{model.__name__.lower()}/"
    ns = Namespace(ns_uri)

    g = Graph()
    g.bind(model.__name__.lower(), ns)

    class_uri = URIRef(ns[model.__name__])

    for instance in model.objects.all():
        subject_uri = URIRef(ns[str(instance.pk)])
        g.add((subject_uri, RDF.type, class_uri))

        for field in model._meta.fields:
            field_name = field.name
            field_value = getattr(instance, field_name)
            predicate_uri = URIRef(ns[field_name])

            if field_value is None:
                continue
            # bool must be checked before int: bool is a subclass of int.
            if isinstance(field_value, bool):
                literal = Literal(field_value, datatype=XSD.boolean)
            elif isinstance(field_value, int):
                literal = Literal(field_value, datatype=XSD.integer)
            elif isinstance(field_value, float):
                literal = Literal(field_value, datatype=XSD.float)
            elif isinstance(field_value, datetime):
                literal = Literal(
                    field_value.isoformat(), datatype=XSD.dateTime
                )
            elif isinstance(field_value, str):
                literal = Literal(field_value, datatype=XSD.string)
            else:
                logger.warning(
                    "Unhandled field type %s for %s.%s; skipping.",
                    type(field_value).__name__,
                    model.__name__,
                    field_name,
                )
                continue
            g.add((subject_uri, predicate_uri, literal))

    metadata_class = URIRef(ns["DumpMetadata"])
    dump_metadata = URIRef(ns["dump_metadata"])
    g.add((dump_metadata, RDF.type, metadata_class))
    g.add((
        dump_metadata,
        URIRef(ns["dump_name"]),
        Literal(dump_name, datatype=XSD.string),
    ))
    g.add((
        dump_metadata,
        URIRef(ns["timestamp"]),
        Literal(datetime.now().isoformat(), datatype=XSD.dateTime),
    ))

    target_dir = output_dir or settings.BASE_DIR
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_file_path = os.path.join(
        target_dir, f"{dump_name}_{timestamp}.ttl"
    )
    with open(dump_file_path, "w", encoding="utf-8") as f:
        f.write(g.serialize(format="turtle"))

    return dump_file_path
