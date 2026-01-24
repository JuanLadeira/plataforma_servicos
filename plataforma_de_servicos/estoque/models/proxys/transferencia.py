from plataforma_de_servicos.estoque.managers.transferencia_manager import (
    TransferenciaManager,
)
from plataforma_de_servicos.estoque.models.estoque_model import Estoque


class Transferencia(Estoque):
    objects = TransferenciaManager()

    class Meta:
        proxy = True
        verbose_name = "Transferencia entre inventário"
        verbose_name_plural = "Transferencias entre inventários"
        ordering = ("-created",)
