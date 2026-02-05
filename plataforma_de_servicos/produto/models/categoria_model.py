from django.db import models
from django.urls import reverse
from django_extensions.db.models import AutoSlugField


class Categoria(models.Model):
    empresa = models.ForeignKey(
        "empresa.Empresa",
        on_delete=models.CASCADE,
        related_name="categorias",
        verbose_name="Empresa",
        null=True,  # Temporary: remove after data migration
        blank=True,
    )
    categoria = models.CharField(max_length=100, db_index=True)
    slug = AutoSlugField(populate_from="categoria")

    class Meta:
        ordering = ("categoria",)
        verbose_name_plural = "Categorias"
        unique_together = [["empresa", "categoria"]]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "slug"],
                name="unique_empresa_categoria_slug",
            ),
        ]

    def __str__(self):
        return self.categoria

    def get_absolute_url(self):
        return reverse("produto-detail", args=[self.slug])
