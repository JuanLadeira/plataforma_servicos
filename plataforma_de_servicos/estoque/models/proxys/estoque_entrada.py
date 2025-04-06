from plataforma_de_servicos.estoque.managers.estoque_entrada_manager import (
    EstoqueEntradaManager,
)
from plataforma_de_servicos.estoque.models.estoque_model import Estoque


class EstoqueEntrada(Estoque):
    objects = EstoqueEntradaManager()

    class Meta:
        proxy = True
        verbose_name = "Entrada de estoque"
        verbose_name_plural = "Entradas de estoque"
        ordering = ("-created",)
