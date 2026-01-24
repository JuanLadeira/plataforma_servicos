from django.apps import AppConfig


class ProdutoConfig(AppConfig):
    name = "plataforma_de_servicos.produto"
    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = "Gestão de Produtos"

    def ready(self):
        # Importa signals para registrá-los
        import plataforma_de_servicos.produto.signals  # noqa: F401
