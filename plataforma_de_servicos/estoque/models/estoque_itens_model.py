from datetime import date
from logging import getLogger

from django.db import models
from django.db import transaction

from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.estoque.exceptions import ProdutoSaldoInsuficienteError
from plataforma_de_servicos.estoque.exceptions import VariacaoSaldoInsuficienteError
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

    @transaction.atomic
    def atualizar_saldo(self):
        """
        Atualiza o saldo do produto/variação relacionado a este item de estoque.

        Se uma variação for especificada, atualiza o estoque da variação.
        Caso contrário, atualiza apenas o estoque do produto base.
        """
        movimento = self.estoque.movimento

        if self.variacao:
            # Atualizar estoque da variação
            self._atualizar_saldo_variacao(movimento)
        else:
            # Atualizar apenas estoque do produto base
            self._atualizar_saldo_produto(movimento)

    def _atualizar_saldo_produto(self, movimento):
        """Atualiza o saldo do produto base."""
        # Guarda o saldo anterior (fotografia histórica)
        self.saldo_anterior = self.produto.estoque

        if movimento == Movimento.ENTRADA.value:
            saldo = self.produto.estoque + self.quantidade

        elif movimento == Movimento.SAIDA.value:
            saldo = self.produto.estoque - self.quantidade

            if saldo < 0:
                raise ProdutoSaldoInsuficienteError(
                    self.produto.produto, self.quantidade,
                )
        elif movimento == Movimento.TRANSFERENCIA.value:
            saldo = self.produto.estoque

        self.saldo = saldo
        self.produto.estoque = saldo
        self.produto.save()
        self.save()

    def _atualizar_saldo_variacao(self, movimento):
        """Atualiza o saldo da variação e do produto base."""
        # Guarda o saldo anterior da variação (fotografia histórica)
        self.saldo_anterior = self.variacao.estoque

        if movimento == Movimento.ENTRADA.value:
            saldo_variacao = self.variacao.estoque + self.quantidade
            saldo_produto = self.produto.estoque + self.quantidade

        elif movimento == Movimento.SAIDA.value:
            saldo_variacao = self.variacao.estoque - self.quantidade
            saldo_produto = self.produto.estoque - self.quantidade

            if saldo_variacao < 0:
                raise VariacaoSaldoInsuficienteError(
                    self.variacao, self.quantidade,
                )
            if saldo_produto < 0:
                raise ProdutoSaldoInsuficienteError(
                    self.produto.produto, self.quantidade,
                )
        elif movimento == Movimento.TRANSFERENCIA.value:
            saldo_variacao = self.variacao.estoque
            saldo_produto = self.produto.estoque

        self.saldo = saldo_variacao
        self.variacao.estoque = saldo_variacao
        self.produto.estoque = saldo_produto
        self.variacao.save()
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
