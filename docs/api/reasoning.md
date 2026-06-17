# `djangordf.reasoning`

Pluggable reasoner layer. Materialise inferred triples into the
configured backend. Pick a reasoner via `settings.DJANGORDF_REASONER`
(dotted import path) or pass one to
{func}`djangordf.reasoning.materialize`.

```{eval-rst}
.. automodule:: djangordf.reasoning
   :members:

.. automodule:: djangordf.reasoning.base
   :members:

.. automodule:: djangordf.reasoning.rdfs
   :members:

.. automodule:: djangordf.reasoning.skos
   :members:

.. automodule:: djangordf.reasoning.owlrl
   :members:
```
