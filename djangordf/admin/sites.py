"""``RDFAdminSite`` — a parallel admin site for ``RDFModel`` classes.

Because ``RDFModel`` is not a ``django.db.models.Model``, registering
it through ``django.contrib.admin.site.register()`` is not possible.
This site keeps its own registry and URL conf; include
``rdf_admin_site.urls`` in your project's URL config to mount it.
"""
from typing import Dict, Optional, Type

from django.urls import path

from .options import RDFModelAdmin


class RDFAdminSite:
    """Per-process registry plus URL conf for RDFModel admins."""

    def __init__(self, name: str = "djangordf_admin"):
        self.name = name
        self._registry: Dict[str, RDFModelAdmin] = {}

    # -- registration -------------------------------------------------------

    def register(
        self,
        model_class,
        admin_class: Optional[Type[RDFModelAdmin]] = None,
    ):
        """Register a model class with an optional admin class.

        Use the two-arg form for explicit registration::

            rdf_admin_site.register(Term, TermAdmin)

        or the decorator form, mirroring Django's
        ``@admin.register(Model)``::

            @rdf_admin_site.register(Term)
            class TermAdmin(RDFModelAdmin):
                list_display = ("iri", "pref_label")
        """
        if admin_class is not None:
            self._do_register(model_class, admin_class)
            return None

        # Decorator form. Also register a default admin immediately so
        # callers that forget the decorator still see the model in the
        # admin index.
        self._do_register(model_class, RDFModelAdmin)

        def _decorator(cls):
            self._do_register(model_class, cls)
            return cls

        return _decorator

    def _do_register(self, model_class, admin_class):
        instance = admin_class(model_class, self)
        self._registry[model_class.__name__] = instance

    def unregister(self, model_class):
        self._registry.pop(model_class.__name__, None)

    def is_registered(self, model_class) -> bool:
        return model_class.__name__ in self._registry

    def get_admin(self, model_name: str) -> RDFModelAdmin:
        return self._registry[model_name]

    def registered(self) -> Dict[str, RDFModelAdmin]:
        return dict(self._registry)

    # -- URLs ---------------------------------------------------------------

    @property
    def urls(self):
        return self.get_urls(), "djangordf_admin", self.name

    def get_urls(self):
        from . import views
        return [
            path(
                "",
                views.index,
                {"site": self},
                name="index",
            ),
            path(
                "<str:model_name>/",
                views.changelist_view,
                {"site": self},
                name="changelist",
            ),
            path(
                "<str:model_name>/add/",
                views.add_view,
                {"site": self},
                name="add",
            ),
            path(
                "<str:model_name>/<path:iri>/delete/",
                views.delete_view,
                {"site": self},
                name="delete",
            ),
            path(
                "<str:model_name>/<path:iri>/",
                views.change_view,
                {"site": self},
                name="change",
            ),
        ]


rdf_admin_site = RDFAdminSite()
