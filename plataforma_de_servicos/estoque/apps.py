from logging import getLogger

from django.apps import AppConfig

logger = getLogger("django")


class EstoqueConfig(AppConfig):
    name = "plataforma_de_servicos.estoque"
    default_auto_field = "django.db.models.BigAutoField"
