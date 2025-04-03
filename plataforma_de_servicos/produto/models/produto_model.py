from django.db import models
from django_extensions.db.models import AutoSlugField

from plataforma_de_servicos.produto.models.categoria_model import Categoria


class Produto(models.Model):
    importado = models.BooleanField(default=False)
    ncm = models.CharField("NCM", max_length=8)
    produto = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="produto", unique=True)
    preco = models.DecimalField("preço", max_digits=7, decimal_places=2)
    estoque = models.IntegerField("estoque atual", default=0)
    estoque_minimo = models.PositiveIntegerField("estoque mínimo", default=0)
    data = models.DateField(null=True, blank=True)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="produtos",
    )

    class Meta:
        ordering = ("produto",)
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"

    def __str__(self):
        return self.produto
