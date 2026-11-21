from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        from core import checks  # noqa: F401, PLC0415 -- Registra checks após carregar os apps.
