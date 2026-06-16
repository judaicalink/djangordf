"""``RDFModelAdmin`` — declarative admin class for ``RDFModel`` classes.

Mirrors ``django.contrib.admin.ModelAdmin``'s declaration shape
without inheriting from it. Honours ``list_display``, ``fields``,
``readonly_fields``, and ``paginate_by``.
"""
from typing import Iterable, Optional, Sequence

from .forms import build_form_class


class RDFModelAdmin:
    """Declarative configuration for an :class:`RDFModel` in the
    :class:`RDFAdminSite` UI."""

    list_display: Sequence[str] = ("iri",)
    fields: Optional[Sequence[str]] = None
    readonly_fields: Sequence[str] = ()
    paginate_by: int = 50

    def __init__(self, model_class, site):
        self.model_class = model_class
        self.site = site

    # -- queryset / object lookup ------------------------------------------

    def get_queryset(self):
        return self.model_class.objects.all()

    def get_object(self, iri):
        return self.model_class.objects.get(iri)

    # -- form generation ----------------------------------------------------

    def get_form_class(self):
        return build_form_class(self.model_class, fields=self.fields)

    # -- presentation -------------------------------------------------------

    def render_list_cell(self, instance, column: str):
        """Stringify one cell of the list view."""
        if column == "iri":
            return str(instance.iri)
        value = getattr(instance, column, None)
        if value is None:
            return ""
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        return str(value)

    def list_columns(self) -> Iterable[str]:
        return tuple(self.list_display)
