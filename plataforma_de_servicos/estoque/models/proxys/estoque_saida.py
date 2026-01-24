from plataforma_de_servicos.estoque.managers.estoque_saida_manager import (
    EstoqueSaidaManager,
)
from plataforma_de_servicos.estoque.models.estoque_model import Estoque


class EstoqueSaida(Estoque):
    objects = EstoqueSaidaManager()

    class Meta:
        proxy = True
        verbose_name = "Saída de estoque"
        verbose_name_plural = "Saídas de estoque"
        ordering = ("-created",)
