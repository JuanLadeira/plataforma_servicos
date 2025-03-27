from plataforma_de_servicos.estoque.managers.estoque_entrada_manager import (
    EstoqueEntradaManager,
)
from plataforma_de_servicos.estoque.models.estoque_model import Estoque


class EstoqueEntrada(Estoque):
    objects = EstoqueEntradaManager()

    class Meta:
        proxy = True
        verbose_name = "registro de entrada de estoque"
        verbose_name_plural = "registros de entrada de estoque"
