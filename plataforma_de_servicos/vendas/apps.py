from django.apps import AppConfig


class VendasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "plataforma_de_servicos.vendas"
    verbose_name = "Vendas"

    def ready(self):
        try:
            import plataforma_de_servicos.vendas.signals  # noqa: F401
        except ImportError:
            pass
