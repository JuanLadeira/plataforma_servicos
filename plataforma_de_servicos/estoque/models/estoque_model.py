from logging import DEBUG
from logging import basicConfig
from logging import getLogger

from django.core.exceptions import ValidationError
from django.db import models
from django.db import transaction

from plataforma_de_servicos.core.models import TimeStampedModel
from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.users.models import User

basicConfig(level=DEBUG)
log = getLogger(__name__)


class Estoque(TimeStampedModel):
    funcionario = models.ForeignKey(User, on_delete=models.CASCADE, blank=True)
    nf = models.PositiveIntegerField("nota fiscal", null=True, blank=True)
    movimento = models.CharField(max_length=1, choices=Movimento.choices, blank=True)
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

        if self.movimento == Movimento.SAIDA.value and not self.inventario_origem:
            message = "Saída requer inventário de origem"
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
        """
        Atualiza o estoque de acordo com o movimento.
        ou seja, entrada ou saída.
        Updates the stock according to the movement.
        that is, entry or exit.
        """
        if not self.processado:
            self.atualizar_estoque()
            self.processado = True
            self.save()

    def atualizar_estoque(self):
        """
        Atualiza o estoque de acordo com a entrada ou saida,
        ou seja, incrementa ou decrementa o saldo dos produtos.
        Updates the stock according to the entry,
        that is, increments the balance of the
        products in this entry.
        """
        itens = self.estoque_itens.all()
        for item in itens:
            if self.movimento == Movimento.ENTRADA.value:
                item.inventario = self.inventario_destino
            elif self.movimento == Movimento.SAIDA.value | self.movimento == Movimento.TRANSFERENCIA.value:
                item.inventario = self.inventario_origem

            saldo = item.produto.estoque
            item.atualizar_saldo()
            saldo = item.produto.estoque
            log.debug("Novo saldo do produto %s é %s", item.produto.produto, saldo)

            self.atualizar_inventario_saldo(item)
            item.save()
        log.debug("Estoque %s processado com sucesso", self.pk)

    def atualizar_inventario_saldo(self, item):
        """Atualiza o saldo específico por inventário"""
        with transaction.atomic():
            if self.movimento == Movimento.ENTRADA.value:
                self._atualizar_inventario(item, self.inventario_destino, item.quantidade)
            elif self.movimento == Movimento.SAIDA.value:
                self._atualizar_inventario(item, self.inventario_origem, -item.quantidade)
            elif self.movimento == Movimento.TRANSFERENCIA.value:
                self._atualizar_inventario(item, self.inventario_origem, -item.quantidade)
                self._atualizar_inventario(item, self.inventario_destino, item.quantidade)

    def _atualizar_inventario(self, item, inventario, quantidade):
        try:
            obj = InventarioSaldo.objects.select_for_update().get(
                inventario=inventario,
                produto=item.produto,
            )
            obj.quantidade += quantidade
            obj.save()
        except InventarioSaldo.DoesNotExist:
            InventarioSaldo.objects.create(
                inventario=inventario,
                produto=item.produto,
                quantidade=max(quantidade, 0),  # Evita valores negativos para novos registros
            )
