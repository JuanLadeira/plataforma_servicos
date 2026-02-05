from django.db import models
from django.db import transaction
from django.utils.translation import gettext as _
from django_extensions.db.fields import AutoSlugField

from plataforma_de_servicos.core.models import TimeStampedModel
from plataforma_de_servicos.produto.models.produto_model import Produto


class Inventario(TimeStampedModel):
    empresa = models.ForeignKey(
        "empresa.Empresa",
        on_delete=models.CASCADE,
        related_name="inventarios",
        verbose_name="Empresa",
        null=True,  # Temporary: remove after data migration
        blank=True,
    )
    nome = models.CharField(max_length=255, verbose_name="Nome")
    slug = AutoSlugField(
        populate_from="nome",
        max_length=255,
        verbose_name="Slug",
    )
    is_ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo",
    )
    exibir_na_vitrine = models.BooleanField(
        default=False,
        verbose_name="Exibir na Vitrine",
        help_text="Se marcado, os produtos deste inventário serão exibidos na página inicial para os clientes.",
    )

    class Meta:
        verbose_name = _("Inventário")
        verbose_name_plural = _("Inventários")
        ordering = ("-created",)
        unique_together = [["empresa", "nome"]]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "slug"],
                name="unique_empresa_inventario_slug",
            ),
        ]

    def __str__(self):
        return _("Inventário: {nome}").format(nome=self.nome)

    def atualizar_estoque(self, produto, quantidade):
        with transaction.atomic():
            saldo, _ = InventarioSaldo.objects.select_for_update().get_or_create(
                inventario=self,
                produto=produto,
                defaults={"quantidade": 0},
            )
            saldo.quantidade += quantidade
            if saldo.quantidade < 0:
                raise ValueError(_("Saldo não pode ser negativo"))
            saldo.save()


class InventarioSaldo(models.Model):
    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.IntegerField(default=0)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("inventario", "produto")
        verbose_name = _("Saldo de Inventário")
        verbose_name_plural = _("Saldos de Inventário")
        ordering = ("produto",)

    def __str__(self):
        return f"{self.produto.categoria}"
