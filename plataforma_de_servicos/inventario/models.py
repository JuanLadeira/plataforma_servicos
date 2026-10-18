from django.core.exceptions import ValidationError
from django.db import models
from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext as _
from django_extensions.db.fields import AutoSlugField

from plataforma_de_servicos.core.models import TimeStampedModel
from plataforma_de_servicos.inventario.exceptions import InventarioPadraoAusenteError
from plataforma_de_servicos.produto.models.atributos import VariacaoProduto
from plataforma_de_servicos.produto.models.produto_model import Produto


class InventarioManager(models.Manager):
    def padrao_da_empresa(self, empresa):
        inventario = self.filter(empresa=empresa, padrao=True, is_ativo=True).first()
        if inventario is None:
            raise InventarioPadraoAusenteError(empresa)
        return inventario


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
    padrao = models.BooleanField(
        default=False,
        verbose_name="Depósito padrão",
        help_text="As ordens aprovadas dão baixa neste depósito. Só um por empresa.",
    )

    objects = InventarioManager()

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
            models.UniqueConstraint(
                fields=["empresa"],
                condition=Q(padrao=True),
                name="unique_inventario_padrao_por_empresa",
            ),
        ]

    def __str__(self):
        return _("Inventário: {nome}").format(nome=self.nome)

    def clean(self):
        super().clean()
        if self.padrao and not self.is_ativo:
            raise ValidationError({"padrao": "O depósito padrão precisa estar ativo."})

    def atualizar_estoque(self, produto, quantidade, variacao=None):
        with transaction.atomic():
            saldo, _created = InventarioSaldo.objects.select_for_update().get_or_create(
                inventario=self,
                produto=produto,
                variacao=variacao,
                defaults={"quantidade": 0},
            )
            saldo.quantidade += quantidade
            if saldo.quantidade < 0:
                raise ValueError(_("Saldo não pode ser negativo"))
            saldo.save()


class InventarioSaldo(models.Model):
    inventario = models.ForeignKey(Inventario, on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    variacao = models.ForeignKey(
        VariacaoProduto,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Variação",
    )
    quantidade = models.IntegerField(default=0)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("inventario", "produto", "variacao")
        verbose_name = _("Saldo de Inventário")
        verbose_name_plural = _("Saldos de Inventário")
        ordering = ("produto", "variacao")

    def __str__(self):
        if self.variacao:
            valores = ", ".join(v.valor for v in self.variacao.valores.all())
            return f"{self.produto.produto} - {valores}" if valores else self.produto.produto
        return self.produto.produto
