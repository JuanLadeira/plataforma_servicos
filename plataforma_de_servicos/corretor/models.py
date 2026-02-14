from decimal import Decimal

from django.db import models
from django.utils import timezone

from plataforma_de_servicos.core.models import TimeStampedModel


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
        null=True,
        blank=True,
    )

    # Identificação
    numero = models.CharField(
        "número",
        max_length=20,
        blank=True,
        help_text="Número único do interesse por empresa (ex: IC-2026-00001)",
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
        "users.Funcionario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interesses",
        verbose_name="corretor responsável",
        help_text="Funcionário/corretor que está atendendo este lead",
        limit_choices_to={"is_corretor": True},
    )

    class Meta:
        verbose_name = "interesse de compra"
        verbose_name_plural = "interesses de compra"
        ordering = ["-created"]
        unique_together = [["empresa", "numero"]]

    def __str__(self):
        if self.numero:
            return f"{self.numero} - {self.nome_cliente}"
        return f"Interesse #{self.pk} - {self.nome_cliente}"

    def save(self, *args, **kwargs):
        # Auto-generate numero if not set and empresa is defined
        if not self.numero and self.empresa_id:
            self.numero = self._gerar_numero()
        super().save(*args, **kwargs)

    def _gerar_numero(self) -> str:
        """Gera número único por empresa no formato IC-YYYY-NNNNN."""
        ano = timezone.now().year
        prefixo = f"IC-{ano}-"

        ultimo = (
            InteresseCompra.objects.filter(
                empresa_id=self.empresa_id,
                numero__startswith=prefixo,
            )
            .order_by("-numero")
            .first()
        )

        if ultimo and ultimo.numero:
            try:
                ultimo_num = int(ultimo.numero.split("-")[-1])
                novo_num = ultimo_num + 1
            except (ValueError, IndexError):
                novo_num = 1
        else:
            novo_num = 1

        return f"{prefixo}{novo_num:05d}"

    @property
    def pode_atender(self) -> bool:
        """Verifica se pode iniciar atendimento (status NOVO)."""
        return self.status == StatusInteresse.NOVO

    @property
    def pode_converter(self) -> bool:
        """Verifica se pode converter para ordem (status EM_ATENDIMENTO)."""
        return self.status == StatusInteresse.EM_ATENDIMENTO

    @property
    def pode_descartar(self) -> bool:
        """Verifica se pode descartar (status NOVO ou EM_ATENDIMENTO)."""
        return self.status in [StatusInteresse.NOVO, StatusInteresse.EM_ATENDIMENTO]

    @property
    def pode_retornar(self) -> bool:
        """Verifica se pode retornar para NOVO (status EM_ATENDIMENTO)."""
        return self.status == StatusInteresse.EM_ATENDIMENTO


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
