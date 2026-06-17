# `djangordf.schema`

Django-migrations-style framework for evolving the RDF schema and
data in the triple store. Define one `Migration` subclass per change
under the configured `DJANGORDF_MIGRATIONS_MODULE`, then run
`python manage.py migrate_rdf`.

```{eval-rst}
.. automodule:: djangordf.schema
   :members:

.. automodule:: djangordf.schema.base
   :members:

.. automodule:: djangordf.schema.operations
   :members:

.. automodule:: djangordf.schema.executor
   :members:

.. automodule:: djangordf.schema.recorder
   :members:
```
