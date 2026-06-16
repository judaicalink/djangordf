"""Django-style admin for ``RDFModel`` classes.

Mirrors ``django.contrib.admin`` shape but runs on its own
:class:`RDFAdminSite` because ``RDFModel`` is not a
``django.db.models.Model``. Register a model with
``rdf_admin_site.register`` and include ``rdf_admin_site.urls`` in
your project's URL config.
"""
from .forms import RDFModelForm
from .options import RDFModelAdmin
from .sites import RDFAdminSite, rdf_admin_site


__all__ = [
    "RDFAdminSite",
    "RDFModelAdmin",
    "RDFModelForm",
    "rdf_admin_site",
]
