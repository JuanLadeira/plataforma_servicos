from datetime import date
from logging import getLogger

from django.db import models
from django.db import transaction

from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.estoque.exceptions import ProdutoSaldoInsuficienteError
from plataforma_de_servicos.estoque.models.estoque_model import Estoque
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.produto.models.produto_model import Produto

log = getLogger("django")


class EstoqueItens(models.Model):
    estoque = models.ForeignKey(
        Estoque,
        on_delete=models.CASCADE,
        related_name="estoque_itens",
    )
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField()
    saldo = models.PositiveIntegerField(blank=True, null=True)
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

    @transaction.atomic
    def atualizar_saldo(self):
        """
        Atualiza o saldo do produto relacionado a este item de estoque.
        """
        if self.estoque.movimento == Movimento.ENTRADA.value:
            saldo = self.produto.estoque + self.quantidade

        elif self.estoque.movimento == Movimento.SAIDA.value:
            saldo = self.produto.estoque - self.quantidade

            if saldo < 0:
                raise ProdutoSaldoInsuficienteError(
                    self.produto.produto, self.quantidade,
                )
        elif self.estoque.movimento == Movimento.TRANSFERENCIA.value:
            saldo = self.produto.estoque

        self.saldo = saldo
        self.produto.estoque = saldo
        self.produto.save()
        self.save()

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
