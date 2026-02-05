from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from plataforma_de_servicos.core.models import TimeStampedModel
from plataforma_de_servicos.corretor.models import Corretor
from plataforma_de_servicos.corretor.models import InteresseCompra
from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.produto.models import VariacaoProduto
from plataforma_de_servicos.users.models import User


class StatusOrdemCompra(models.TextChoices):
    PENDENTE_APROVACAO = "PENDENTE_APROVACAO", "Pendente de Aprovação"
    APROVADA = "APROVADA", "Aprovada"
    REJEITADA = "REJEITADA", "Rejeitada"
    FATURADA = "FATURADA", "Faturada"
    CONCLUIDA = "CONCLUIDA", "Concluída"
    CANCELADA = "CANCELADA", "Cancelada"


class OrdemCompra(TimeStampedModel):
    """Ordem de Compra gerada a partir de um interesse convertido."""

    empresa = models.ForeignKey(
        "empresa.Empresa",
        on_delete=models.CASCADE,
        related_name="ordens_compra",
        verbose_name="Empresa",
        null=True,  # Temporary: remove after data migration
        blank=True,
    )

    # Identificação
    numero = models.CharField(
        "número",
        max_length=20,
        help_text="Número único da ordem (ex: OC-2026-00001)",
    )

    # Origem
    interesse = models.OneToOneField(
        InteresseCompra,
        on_delete=models.PROTECT,
        related_name="ordem_compra",
        verbose_name="interesse de origem",
    )

    # Dados do Cliente (copiados do interesse para histórico)
    nome_cliente = models.CharField("nome do cliente", max_length=255)
    email_cliente = models.EmailField("e-mail do cliente")
    telefone_cliente = models.CharField("telefone do cliente", max_length=20)

    # Valores
    valor_total = models.DecimalField(
        "valor total",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # Status e Fluxo
    status = models.CharField(
        "status",
        max_length=20,
        choices=StatusOrdemCompra.choices,
        default=StatusOrdemCompra.PENDENTE_APROVACAO,
    )

    # Aprovação
    aprovado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordens_aprovadas",
        verbose_name="aprovado por",
    )
    data_aprovacao = models.DateTimeField(
        "data de aprovação",
        null=True,
        blank=True,
    )
    motivo_rejeicao = models.TextField(
        "motivo da rejeição",
        blank=True,
    )

    # Corretor responsável
    corretor = models.ForeignKey(
        Corretor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordens",
        verbose_name="corretor responsável",
    )

    # Observações
    observacoes = models.TextField("observações", blank=True)

    class Meta:
        verbose_name = "ordem de compra"
        verbose_name_plural = "ordens de compra"
        ordering = ["-created"]
        unique_together = [["empresa", "numero"]]

    def __str__(self):
        return f"{self.numero} - {self.nome_cliente}"

    def clean(self):
        super().clean()
        # Rejeição requer motivo
        if self.status == StatusOrdemCompra.REJEITADA and not self.motivo_rejeicao:
            raise ValidationError({
                "motivo_rejeicao": "É obrigatório informar o motivo da rejeição."
            })

    @property
    def pode_aprovar(self):
        return self.status == StatusOrdemCompra.PENDENTE_APROVACAO

    @property
    def pode_rejeitar(self):
        return self.status == StatusOrdemCompra.PENDENTE_APROVACAO

    @property
    def pode_faturar(self):
        return self.status == StatusOrdemCompra.APROVADA

    @property
    def pode_cancelar(self):
        return self.status in [
            StatusOrdemCompra.PENDENTE_APROVACAO,
            StatusOrdemCompra.APROVADA,
        ]

    @property
    def pode_concluir(self):
        return self.status == StatusOrdemCompra.FATURADA


class ItemOrdemCompra(models.Model):
    """Itens de uma ordem de compra."""

    ordem = models.ForeignKey(
        OrdemCompra,
        on_delete=models.CASCADE,
        related_name="itens",
        verbose_name="ordem",
    )

    # Referência ao produto real (opcional - pode não existir se veio de ItemInteresse)
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="produto",
    )
    variacao = models.ForeignKey(
        VariacaoProduto,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="variação",
    )

    # Dados no momento da criação (para histórico)
    produto_nome = models.CharField(
        "nome do produto",
        max_length=255,
        help_text="Nome do produto no momento da criação da ordem",
    )
    variacao_info = models.CharField(
        "informações da variação",
        max_length=255,
        blank=True,
        help_text="Descrição da variação (ex: Cor: Azul, Tamanho: M)",
    )

    quantidade = models.PositiveIntegerField("quantidade", default=1)
    preco_unitario = models.DecimalField(
        "preço unitário",
        max_digits=10,
        decimal_places=2,
    )

    class Meta:
        verbose_name = "item da ordem"
        verbose_name_plural = "itens da ordem"

    def __str__(self):
        return f"{self.quantidade}x {self.produto_nome}"

    @property
    def subtotal(self):
        return self.quantidade * self.preco_unitario
