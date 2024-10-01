# Djangordf

**Djangordf** is a powerful Django library designed to manage RDF (Resource Description Framework) data directly from Django models. It provides full **CRUD functionality** for RDF data, allowing developers to easily create, read, update, and delete RDF triples. The library also supports **ontology creation** and **automatic synchronization** with external triple stores, making it a perfect solution for building semantically enriched web applications.

## Features

- Full **CRUD support** for RDF data
- **Ontology management** and custom RDF mappings
- **Automatic syncing** with external triple stores (e.g., RDF4J, Blazegraph)
- **SPARQL support** for querying RDF data
- Integration of **external RDF graphs** as alternative data sources
- Easy setup and usage within Django projects

## Installation

To install Djangordf, run the following command:

```bash
pip install djangordf
```

## Usage

Add `djangordf` to your Django project's `INSTALLED_APPS`.
Define RDF mappings for your Django models using the provided admin interface.
Use the API to interact with RDF triples or integrate them into your application.

## License

This project is licensed under the MIT License.
