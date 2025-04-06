from django.db import models
from django.utils.translation import gettext as _

from plataforma_de_servicos.core.models import TimeStampedModel


# Create your models here.
class Inventario(TimeStampedModel):
    nome = models.CharField(max_length=255, unique=True, verbose_name="Nome")
    slug = models.SlugField(
        max_length=255,
        unique=True,
        verbose_name="Identificador",
    )
    is_ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo",
    )

    class Meta:
        verbose_name = _("Inventário")
        verbose_name_plural = _("Inventários")
        ordering = ("-created",)

    def __str__(self):
        return _("Inventário: {nome}").format(nome=self.nome)


class Transferencia(TimeStampedModel):
    """
    Model to represent the transfer of items between inventories.
    """
    inventario_origem = models.ForeignKey(
        Inventario,
        on_delete=models.CASCADE,
        related_name="transferencias_origem",
        verbose_name=_("Inventário de origem"),
    )
    inventario_destino = models.ForeignKey(
        Inventario,
        on_delete=models.CASCADE,
        related_name="transferencias_destino",
        verbose_name=_("Inventário de destino"),
    )
    funcionario_responsavel = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="transferencias_responsavel",
        verbose_name=_("Funcionário responsável"),
    )
    status = models.CharField(
        max_length=50,
        choices=[
            ("pendente", _("Pendente")),
            ("concluida", _("Concluída")),
            ("cancelada", _("Cancelada")),
        ],
        default="pendente",
        verbose_name=_("Status"),
    )
    data_solicitacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Data de solicitação"),
    )
    data_conclusao = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Data de conclusão"),
    )
    data_cancelamento = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Data de cancelamento"),
    )
    observacoes = models.TextField(
        blank=True,
        verbose_name=_("Observações"),
    )
    class Meta:
        verbose_name = _("Transferência")
        verbose_name_plural = _("Transferências")
        ordering = ("-created",)

    def __str__(self):
        return _("Transferência: {id}").format(id=self.id)


class TransferenciaItens(TimeStampedModel):
    """
    Model to represent the items involved in a transfer.
    """
    transferencia = models.ForeignKey(
        Transferencia,
        on_delete=models.CASCADE,
        related_name="itens",
        verbose_name=_("Transferência"),
    )
    produto = models.ForeignKey(
        "estoque.Produto",
        on_delete=models.CASCADE,
        related_name="transferencias_itens",
        verbose_name=_("Produto"),
    )
    quantidade = models.IntegerField(
        verbose_name=_("Quantidade"),
    )

    class Meta:
        verbose_name = _("Item de Transferência")
        verbose_name_plural = _("Itens de Transferência")

    @property
    def inventario_origem(self):
        """
        Get the origin inventory of the transfer.
        """
        return self.transferencia.inventario_origem

    @property
    def inventario_destino(self):
        """
        Get the destination inventory of the transfer.
        """
        return self.transferencia.inventario_destino
