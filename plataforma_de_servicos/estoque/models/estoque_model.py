from logging import DEBUG
from logging import basicConfig
from logging import getLogger

from django.db import models
from django.db import transaction

from plataforma_de_servicos.core.models import TimeStampedModel
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.users.models import User

MOVIMENTO = (
    ("e", "entrada"),
    ("s", "saída"),
)


basicConfig(level=DEBUG)
log = getLogger(__name__)


class Estoque(TimeStampedModel):
    funcionario = models.ForeignKey(User, on_delete=models.CASCADE, blank=True)
    nf = models.PositiveIntegerField("nota fiscal", null=True, blank=True)
    movimento = models.CharField(max_length=1, choices=MOVIMENTO, blank=True)
    processado = models.BooleanField(default=False)
    data = models.DateField("data", auto_now_add=True, help_text="Data do movimento")
    inventario = models.ForeignKey(
        Inventario,
        on_delete=models.CASCADE,
        related_name="estoque",
        verbose_name="Inventário",
    )

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        if self.nf:
            return "{} - {} - {}".format(
                self.pk, self.nf, self.created.strftime("%d-%m-%Y"),
            )
        return "{} --- {}".format(self.pk, self.created.strftime("%d-%m-%Y"))

    def get_movimento_display(self):
        movimento = self.movimento
        if movimento == "e":
            return MOVIMENTO[0][1].capitalize()
        return MOVIMENTO[1][1].capitalize()

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
            self.atualizar_estoque_entrada_ou_saida()
            self.processado = True
            self.save()

    def atualizar_estoque_entrada_ou_saida(self):
        """
        Atualiza o estoque de acordo com a entrada ou saida,
        ou seja, incrementa ou decrementa o saldo dos produtos.
        Updates the stock according to the entry,
        that is, increments the balance of the
        products in this entry.
        """
        itens = self.estoque_itens.all()
        for item in itens:
            saldo = item.produto.estoque
            item.atualizar_saldo()
            saldo = item.produto.estoque
            log.debug("Novo saldo do produto %s é %s", item.produto.produto, saldo)
