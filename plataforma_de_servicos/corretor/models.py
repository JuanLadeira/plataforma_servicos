from decimal import Decimal

from django.db import models

from plataforma_de_servicos.core.models import TimeStampedModel
from plataforma_de_servicos.users.models import User


class Corretor(TimeStampedModel):
    """Modelo para representar um corretor/vendedor no sistema."""

    empresa = models.ForeignKey(
        "empresa.Empresa",
        on_delete=models.CASCADE,
        related_name="corretores",
        verbose_name="Empresa",
        null=True,  # Temporary: remove after data migration
        blank=True,
    )
    nome = models.CharField("nome", max_length=255)
    email = models.EmailField("e-mail")
    telefone = models.CharField("telefone", max_length=20, blank=True)
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="corretor",
        verbose_name="usuário",
        help_text="Usuário associado ao corretor (opcional)",
    )
    ativo = models.BooleanField("ativo", default=True)

    class Meta:
        verbose_name = "corretor"
        verbose_name_plural = "corretores"
        ordering = ["nome"]
        unique_together = [["empresa", "email"]]

    def __str__(self):
        return self.nome


class StatusInteresse(models.TextChoices):
    NOVO = "NOVO", "Novo"
    EM_ATENDIMENTO = "EM_ATENDIMENTO", "Em Atendimento"
    CONVERTIDO = "CONVERTIDO", "Convertido"
    DESCARTADO = "DESCARTADO", "Descartado"


class InteresseCompra(TimeStampedModel):
    """Modelo para armazenar demonstrações de interesse (leads)."""

    empresa = models.ForeignKey(
        "empresa.Empresa",
        on_delete=models.CASCADE,
        related_name="interesses_compra",
        verbose_name="Empresa",
        null=True,  # Temporary: remove after data migration
        blank=True,
    )

    # Dados do cliente/lead
    nome_cliente = models.CharField("nome do cliente", max_length=255)
    email_cliente = models.EmailField("e-mail do cliente")
    telefone_cliente = models.CharField("telefone do cliente", max_length=20)
    mensagem = models.TextField("mensagem", blank=True, help_text="Observações adicionais do cliente")

    # Valor total dos itens de interesse
    valor_total = models.DecimalField(
        "valor total",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # Status e atribuição
    status = models.CharField(
        "status",
        max_length=20,
        choices=StatusInteresse.choices,
        default=StatusInteresse.NOVO,
    )
    corretor = models.ForeignKey(
        Corretor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interesses",
        verbose_name="corretor responsável",
        help_text="Corretor que está atendendo este lead",
    )

    class Meta:
        verbose_name = "interesse de compra"
        verbose_name_plural = "interesses de compra"
        ordering = ["-created"]

    def __str__(self):
        return f"Interesse #{self.pk} - {self.nome_cliente}"


class ItemInteresse(models.Model):
    """Itens associados a um interesse de compra."""

    interesse = models.ForeignKey(
        InteresseCompra,
        on_delete=models.CASCADE,
        related_name="itens",
        verbose_name="interesse",
    )
    produto_nome = models.CharField("produto", max_length=255)
    variacao_info = models.CharField(
        "variação",
        max_length=255,
        blank=True,
        help_text="Informações da variação (ex: Cor: Azul, Tamanho: M)",
    )
    quantidade = models.PositiveIntegerField("quantidade", default=1)
    preco_unitario = models.DecimalField(
        "preço unitário",
        max_digits=10,
        decimal_places=2,
    )

    class Meta:
        verbose_name = "item do interesse"
        verbose_name_plural = "itens do interesse"

    def __str__(self):
        return f"{self.quantidade}x {self.produto_nome}"

    @property
    def subtotal(self):
        return self.quantidade * self.preco_unitario
