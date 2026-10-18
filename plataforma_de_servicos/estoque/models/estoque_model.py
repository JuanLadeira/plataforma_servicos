from logging import DEBUG
from logging import basicConfig
from logging import getLogger

from django.core.exceptions import ValidationError
from django.db import connection
from django.db import models
from django.db import transaction

from plataforma_de_servicos.core.models import TimeStampedModel
from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.estoque.choices.origem_saida import OrigemSaida
from plataforma_de_servicos.estoque.exceptions import InventarioSaldoInsuficienteError
from plataforma_de_servicos.estoque.exceptions import ProdutoSaldoInsuficienteError
from plataforma_de_servicos.estoque.exceptions import VariacaoSaldoInsuficienteError
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.users.models import User
from plataforma_de_servicos.vendas.models.ordem_compra import OrdemCompra

basicConfig(level=DEBUG)
log = getLogger(__name__)


def _nome_item(produto, variacao):
    if variacao is None:
        return produto.produto
    valores = ", ".join(v.valor for v in variacao.valores.all())
    return f"{produto.produto} - {valores}" if valores else f"{produto.produto} - variação #{variacao.pk}"


class Estoque(TimeStampedModel):
    empresa = models.ForeignKey(
        "empresa.Empresa",
        on_delete=models.CASCADE,
        related_name="estoques",
        verbose_name="Empresa",
        null=True,  # Temporary: remove after data migration
        blank=True,
    )
    funcionario = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    nf = models.PositiveIntegerField("nota fiscal", null=True, blank=True)
    movimento = models.CharField(max_length=1, choices=Movimento.choices, blank=True)
    origem_saida = models.CharField(
        "Origem da Saída",
        max_length=15,
        choices=OrigemSaida.choices,
        null=True,
        blank=True,
        help_text="Motivo/origem da saída de estoque",
    )
    ordem_compra = models.ForeignKey(
        OrdemCompra,
        on_delete=models.PROTECT,
        verbose_name="Ordem de Compra",
        related_name="saidas_estoque",
        null=True,
        blank=True,
        help_text="Ordem de compra que originou esta saída de estoque",
    )
    observacao = models.TextField(
        "Observações",
        null=True,
        blank=True,
        help_text="Observações adicionais sobre o movimento",
    )
    processado = models.BooleanField(default=False)
    data = models.DateField("data", auto_now_add=True, help_text="Data do movimento")
    inventario_origem = models.ForeignKey(
        Inventario,
        on_delete=models.CASCADE,
        related_name="estoque_origem",
        verbose_name="Inventário de Origem",
        null=True,
        blank=True,
    )
    inventario_destino = models.ForeignKey(
        Inventario,
        on_delete=models.CASCADE,
        related_name="estoque_destino",
        verbose_name="Inventário de Destino",
        null=True,
        blank=True,
    )
    class Meta:
        ordering = ("-created",)

    def clean(self):
        """Validação de consistência dos inventários"""
        if self.movimento == Movimento.ENTRADA.value and not self.inventario_destino:
            message = "Entrada requer inventário de destino"
            raise ValidationError(message=message)

        if self.movimento == Movimento.SAIDA.value:
            if not self.inventario_origem:
                message = "Saída requer inventário de origem"
                raise ValidationError(message=message)

            # Se origem for PEDIDO, exige a ordem de compra
            if self.origem_saida == OrigemSaida.PEDIDO.value and not self.ordem_compra:
                message = "Saída por pedido requer uma ordem de compra"
                raise ValidationError(message=message)

        if self.movimento == Movimento.TRANSFERENCIA.value and not (self.inventario_origem and self.inventario_destino):
            message = "Transferência requer origem e destino"
            raise ValidationError(message=message)

    def __str__(self):
        if self.nf:
            return "{} - {} - {}".format(
                self.pk, self.nf, self.created.strftime("%d-%m-%Y"),
            )
        return "{} --- {}".format(self.pk, self.created.strftime("%d-%m-%Y"))

    def get_movimento_display(self):
        movimento = self.movimento
        if movimento == Movimento.ENTRADA.value:
            return Movimento.ENTRADA.label
        if movimento == Movimento.SAIDA.value:
            return Movimento.SAIDA.label
        if movimento == Movimento.TRANSFERENCIA.value:
            return Movimento.TRANSFERENCIA.label
        return "Não definido"

    def nf_formated(self):
        if self.nf:
            return str(self.nf).zfill(3)
        return "---"

    @transaction.atomic
    def processar(self):
        """Aplica a movimentação aos saldos uma única vez, com as linhas travadas.

        Trava a movimentação e depois os saldos em ordem fixa (ver estoque/locks.py).
        Uma segunda chamada, mesmo concorrente, não faz nada. Qualquer saldo que ficaria
        negativo (produto, variação ou depósito) levanta o erro e desfaz tudo.
        """
        from plataforma_de_servicos.estoque.locks import travar_saldos

        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout = '5s'")
        estoque = type(self).objects.select_for_update().get(pk=self.pk)
        if estoque.processado:
            self.processado = True
            return
        itens = list(estoque.estoque_itens.select_related("produto", "variacao").order_by("pk"))
        travas = travar_saldos(estoque, itens)
        for item in itens:
            estoque._aplicar_item(item, travas)
        for variacao in travas.variacoes.values():
            variacao.save(update_fields=["estoque"])
        for produto in travas.produtos.values():
            produto.save(update_fields=["estoque"])
        for saldo in travas.saldos.values():
            saldo.save(update_fields=["quantidade", "atualizado_em"])
        estoque.processado = True
        estoque.save(update_fields=["processado", "modified"])
        self.processado = True
        log.debug("Estoque %s processado com sucesso", self.pk)

    def _aplicar_item(self, item, travas):
        """Calcula e aplica o item sobre as instâncias travadas, sem gravar produto, variação e saldos."""
        produto = travas.produtos[item.produto_id]
        variacao = travas.variacoes.get(item.variacao_id)
        quantidade = item.quantidade
        origem = (self.inventario_origem_id, item.produto_id, item.variacao_id)
        destino = (self.inventario_destino_id, item.produto_id, item.variacao_id)

        if self.movimento == Movimento.ENTRADA.value:
            delta_total, deltas = quantidade, {destino: quantidade}
            item.inventario_id = self.inventario_destino_id
        elif self.movimento == Movimento.SAIDA.value:
            delta_total, deltas = -quantidade, {origem: -quantidade}
            item.inventario_id = self.inventario_origem_id
        else:  # transferência: produto e variação não mudam
            delta_total, deltas = 0, {origem: -quantidade, destino: quantidade}
            item.inventario_id = self.inventario_origem_id

        referencia = variacao or produto
        item.saldo_anterior = referencia.estoque or 0

        if variacao is not None and variacao.estoque + delta_total < 0:
            raise VariacaoSaldoInsuficienteError(variacao, quantidade)
        if (produto.estoque or 0) + delta_total < 0:
            raise ProdutoSaldoInsuficienteError(produto.produto, quantidade)
        for chave, delta in deltas.items():
            saldo = travas.saldos[chave]
            if saldo.quantidade + delta < 0:
                raise InventarioSaldoInsuficienteError(saldo, quantidade, item=_nome_item(produto, variacao))

        if variacao is not None:
            variacao.estoque += delta_total
        produto.estoque = (produto.estoque or 0) + delta_total
        for chave, delta in deltas.items():
            travas.saldos[chave].quantidade += delta

        item.saldo = referencia.estoque
        item.save(update_fields=["saldo_anterior", "saldo", "inventario"])
