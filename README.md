# Django RDF

[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://GitHub.com/judaicalink/djangordf/graphs/commit-activity)

[![GitHub license](https://img.shields.io/github/license/Naereen/StrapDown.js.svg)](https://github.com/judaicalink/djangordf/blob/master/LICENSE)

[![forthebadge made-with-python](http://ForTheBadge.com/images/badges/made-with-python.svg)](https://www.python.org/)

[![PyPI download month](https://img.shields.io/pypi/dm/ansicolortags.svg)](https://pypi.org/project/djangordf/)

[![PyPI version fury.io](https://badge.fury.io/py/ansicolortags.svg)](https://pypi.org/project/djangordf/)


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
