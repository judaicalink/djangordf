"""Lifecycle signals for ``RDFModel`` instances.

Use these to hook into the persistence path without subclassing the
manager. Each signal sends two keyword arguments: ``sender`` (the
model class) and ``instance`` (the instance being saved or deleted).

``pre_save`` and ``post_save`` fire around a single-instance
:meth:`RDFManager.save` call. ``pre_delete`` and ``post_delete``
fire around :meth:`RDFManager.delete`.

Bulk operations (``bulk_create``, ``bulk_update``, ``bulk_delete``)
**do not** fire these signals — matching Django's
``Model.objects.bulk_create`` convention. If you need signal
semantics for every instance, use the single-instance path.
"""
from django.dispatch import Signal


pre_save = Signal()
post_save = Signal()
pre_delete = Signal()
post_delete = Signal()
