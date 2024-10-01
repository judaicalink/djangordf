from rdflib import Graph, Literal, RDF, URIRef
from rdflib.namespace import FOAF, XSD, Namespace
from datetime import datetime
import os
from django.conf import settings


def export_model_to_rdf(model, dump_name):
    # Namespace basierend auf dem Model
    ns = Namespace(f"http://example.org/{model.__name__.lower()}/")

    # Erstellen eines Graphen
    g = Graph()

    # Hinzufügen von Modelldaten zum Graphen
    for instance in model.objects.all():
        subject_uri = URIRef(ns[str(instance.id)])

        # Alle Felder des Modells durchgehen und zu RDF konvertieren
        for field in model._meta.fields:
            field_name = field.name
            field_value = getattr(instance, field_name)

            # Feld-URI und Wert als Literal hinzufügen
            predicate_uri = URIRef(ns[field_name])
            if isinstance(field_value, str):
                g.add((subject_uri, predicate_uri, Literal(field_value, datatype=XSD.string)))
            elif isinstance(field_value, int):
                g.add((subject_uri, predicate_uri, Literal(field_value, datatype=XSD.integer)))
            elif isinstance(field_value, float):
                g.add((subject_uri, predicate_uri, Literal(field_value, datatype=XSD.float)))
            elif isinstance(field_value, bool):
                g.add((subject_uri, predicate_uri, Literal(field_value, datatype=XSD.boolean)))
            elif isinstance(field_value, datetime):
                g.add((subject_uri, predicate_uri, Literal(field_value, datatype=XSD.dateTime)))
            else:
                # Andere Typen können hier behandelt werden
                pass

    # Name und Zeitstempel des Dumps hinzufügen
    dump_metadata = URIRef(ns["dump_metadata"])
    g.add((dump_metadata, RDF.type, Literal("Dump Metadata", datatype=XSD.string)))
    g.add((dump_metadata, URIRef(ns["dump_name"]), Literal(dump_name, datatype=XSD.string)))
    g.add((dump_metadata, URIRef(ns["timestamp"]), Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))

    # Den Graphen als RDF-Turtle speichern
    dump_file_path = os.path.join(settings.BASE_DIR, f"{dump_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ttl")
    with open(dump_file_path, 'w', encoding='utf-8') as f:
        f.write(g.serialize(format='turtle'))

    return dump_file_path
