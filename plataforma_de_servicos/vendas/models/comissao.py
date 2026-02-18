"""
Modelo de Comissão para tracking de comissões de vendedores.
"""
from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _

from plataforma_de_servicos.core.models import TimeStampedModel


class StatusComissao(models.TextChoices):
    PENDENTE = "PENDENTE", _("Pendente")
    APROVADA = "APROVADA", _("Aprovada")
    PAGA = "PAGA", _("Paga")
    CANCELADA = "CANCELADA", _("Cancelada")


class Comissao(TimeStampedModel):
    """
    Registra comissões de vendedores sobre ordens de compra.

    A comissão é calculada com base em:
    - Percentual definido (pode ser por empresa, categoria ou vendedor)
    - Valor total da ordem de compra
    """

    empresa = models.ForeignKey(
        "empresa.Empresa",
        on_delete=models.CASCADE,
        related_name="comissoes",
        verbose_name=_("Empresa"),
        null=True,
        blank=True,
    )

    # Vínculo com ordem e vendedor
    ordem = models.ForeignKey(
        "vendas.OrdemCompra",
        on_delete=models.CASCADE,
        related_name="comissoes",
        verbose_name=_("Ordem de Compra"),
    )
    funcionario = models.ForeignKey(
        "users.Funcionario",
        on_delete=models.PROTECT,
        related_name="comissoes",
        verbose_name=_("Vendedor"),
    )

    # Valores
    percentual = models.DecimalField(
        _("Percentual"),
        max_digits=5,
        decimal_places=2,
        help_text=_("Percentual de comissão (ex: 5.00 para 5%)"),
    )
    valor_base = models.DecimalField(
        _("Valor Base"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Valor total da ordem sobre o qual a comissão é calculada"),
    )
    valor_comissao = models.DecimalField(
        _("Valor da Comissão"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Valor calculado da comissão (valor_base * percentual / 100)"),
    )

    # Status e pagamento
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=StatusComissao.choices,
        default=StatusComissao.PENDENTE,
    )
    data_aprovacao = models.DateField(
        _("Data de Aprovação"),
        null=True,
        blank=True,
    )
    data_pagamento = models.DateField(
        _("Data de Pagamento"),
        null=True,
        blank=True,
    )

    # Observações
    observacoes = models.TextField(
        _("Observações"),
        blank=True,
    )

    class Meta:
        verbose_name = _("Comissão")
        verbose_name_plural = _("Comissões")
        ordering = ["-created"]
        # Uma comissão por vendedor por ordem
        unique_together = [["ordem", "funcionario"]]

    def __str__(self):
        return f"Comissão {self.ordem.numero} - {self.funcionario.nome}"

    def save(self, *args, **kwargs):
        # Auto-preenche empresa da ordem
        if not self.empresa_id and self.ordem_id:
            self.empresa = self.ordem.empresa

        # Calcula valor da comissão se não informado
        if not self.valor_comissao and self.valor_base and self.percentual:
            self.valor_comissao = self.calcular_valor()

        super().save(*args, **kwargs)

    def calcular_valor(self) -> Decimal:
        """Calcula o valor da comissão baseado no percentual e valor base."""
        if not self.valor_base or not self.percentual:
            return Decimal("0.00")
        return (self.valor_base * self.percentual / Decimal("100")).quantize(
            Decimal("0.01")
        )

    @property
    def pode_aprovar(self) -> bool:
        """Verifica se a comissão pode ser aprovada."""
        return self.status == StatusComissao.PENDENTE

    @property
    def pode_pagar(self) -> bool:
        """Verifica se a comissão pode ser paga."""
        return self.status == StatusComissao.APROVADA

    @property
    def pode_cancelar(self) -> bool:
        """Verifica se a comissão pode ser cancelada."""
        return self.status in [StatusComissao.PENDENTE, StatusComissao.APROVADA]


class ConfiguracaoComissao(TimeStampedModel):
    """
    Configuração de percentuais de comissão por empresa.

    Permite definir regras de comissão:
    - Percentual padrão da empresa
    - Percentual por categoria de produto
    - Percentual específico por vendedor
    """

    empresa = models.OneToOneField(
        "empresa.Empresa",
        on_delete=models.CASCADE,
        related_name="configuracao_comissao",
        verbose_name=_("Empresa"),
    )

    # Percentual padrão
    percentual_padrao = models.DecimalField(
        _("Percentual Padrão"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("5.00"),
        help_text=_("Percentual padrão de comissão para todos os vendedores"),
    )

    # Configurações opcionais
    aplica_sobre_desconto = models.BooleanField(
        _("Aplica sobre valor com desconto"),
        default=True,
        help_text=_("Se marcado, a comissão é calculada sobre o valor final (com desconto)"),
    )

    class Meta:
        verbose_name = _("Configuração de Comissão")
        verbose_name_plural = _("Configurações de Comissão")

    def __str__(self):
        return f"Configuração de Comissão - {self.empresa.nome}"


class ComissaoCategoria(models.Model):
    """
    Percentual de comissão específico por categoria.

    Permite definir comissões diferentes para categorias de produtos.
    Ex: Carros podem ter 2% e Peças podem ter 5%.
    """

    configuracao = models.ForeignKey(
        ConfiguracaoComissao,
        on_delete=models.CASCADE,
        related_name="comissoes_categoria",
        verbose_name=_("Configuração"),
    )
    categoria = models.ForeignKey(
        "produto.Categoria",
        on_delete=models.CASCADE,
        related_name="comissoes_configuradas",
        verbose_name=_("Categoria"),
    )
    percentual = models.DecimalField(
        _("Percentual"),
        max_digits=5,
        decimal_places=2,
        help_text=_("Percentual de comissão para esta categoria"),
    )

    class Meta:
        verbose_name = _("Comissão por Categoria")
        verbose_name_plural = _("Comissões por Categoria")
        unique_together = [["configuracao", "categoria"]]

    def __str__(self):
        return f"{self.categoria.categoria}: {self.percentual}%"


class ComissaoVendedor(models.Model):
    """
    Percentual de comissão específico por vendedor.

    Permite definir comissões personalizadas para vendedores específicos.
    Ex: Vendedor sênior pode ter 7%, júnior pode ter 3%.
    """

    configuracao = models.ForeignKey(
        ConfiguracaoComissao,
        on_delete=models.CASCADE,
        related_name="comissoes_vendedor",
        verbose_name=_("Configuração"),
    )
    funcionario = models.ForeignKey(
        "users.Funcionario",
        on_delete=models.CASCADE,
        related_name="comissoes_configuradas",
        verbose_name=_("Vendedor"),
    )
    percentual = models.DecimalField(
        _("Percentual"),
        max_digits=5,
        decimal_places=2,
        help_text=_("Percentual de comissão para este vendedor"),
    )

    class Meta:
        verbose_name = _("Comissão por Vendedor")
        verbose_name_plural = _("Comissões por Vendedor")
        unique_together = [["configuracao", "funcionario"]]

    def __str__(self):
        return f"{self.funcionario.nome}: {self.percentual}%"
