from django.apps import AppConfig


class TodosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "todos"

    def ready(self) -> None:
        # Import signal handlers.
        from . import signals  # noqa: F401

