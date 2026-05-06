"""Shared test fixtures and helpers for the djangordf suite."""
from rdflib import Graph


def load_graph(path):
    """Load a Turtle file into a fresh rdflib Graph."""
    g = Graph()
    g.parse(path, format="turtle")
    return g
