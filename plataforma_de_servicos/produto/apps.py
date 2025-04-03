from django.apps import AppConfig


class ProdutoConfig(AppConfig):
    name = "plataforma_de_servicos.produto"
    default_auto_field = "django.db.models.BigAutoField"
    verbose_name= "Gestão de Produtos"
