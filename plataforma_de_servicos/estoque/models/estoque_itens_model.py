from datetime import date
from logging import getLogger

from django.db import models

from plataforma_de_servicos.estoque.models.estoque_model import Estoque
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.produto.models.atributos import VariacaoProduto
from plataforma_de_servicos.produto.models.produto_model import Produto

log = getLogger("django")


class EstoqueItens(models.Model):
    estoque = models.ForeignKey(
        Estoque,
        on_delete=models.CASCADE,
        related_name="estoque_itens",
    )
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    variacao = models.ForeignKey(
        VariacaoProduto,
        on_delete=models.CASCADE,
        related_name="estoque_itens",
        verbose_name="Variação",
        null=True,
        blank=True,
        help_text="Selecione a variação do produto (se houver). O estoque será descontado da variação.",
    )
    quantidade = models.PositiveIntegerField()
    saldo_anterior = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Saldo Anterior",
        help_text="Saldo da variação/produto antes da operação (fotografia histórica)",
    )
    saldo = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Saldo Após",
        help_text="Saldo da variação/produto após a operação",
    )
    inventario = models.ForeignKey(
        Inventario,
        on_delete=models.CASCADE,
        related_name="estoque_itens",
        verbose_name="Inventário",
    )

    class Meta:
        ordering = ("pk",)
        verbose_name = "item"
        verbose_name_plural = "itens do registro de estoque"

    def __str__(self):
        return f"{self.pk} - {self.estoque.pk} - {self.produto}"

    def save(self, *args, **kwargs):
        """
        Salva o item de estoque.
        """
        super().save(*args, **kwargs)

    def data(self) -> date:
        return self.estoque.data

    def movimento(self) -> str:
        return self.estoque.get_movimento_display()

    def nf(self) -> int:
        return self.estoque.nf

    def clean(self):
        """
        Valida o item de estoque antes de salvar.
        """
        if self.quantidade <= 0:
            message = (
                "A quantidade deve ser maior que zero."
                f"Quantidade: {self.quantidade}"
            )
            raise ValueError(message)
