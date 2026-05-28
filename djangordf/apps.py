from django.apps import AppConfig


class DjangordfConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "djangordf"
    verbose_name = "Django RDF"

    def ready(self) -> None:
        from .namespaces import apply_namespace_settings
        apply_namespace_settings()
