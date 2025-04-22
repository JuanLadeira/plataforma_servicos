from django.db import models
from django.urls import reverse
from django_extensions.db.models import AutoSlugField


class Categoria(models.Model):
    categoria = models.CharField(max_length=100, unique=True, db_index=True)
    slug = AutoSlugField(populate_from="categoria", unique=True)

    class Meta:
        ordering = ("categoria",)
        verbose_name_plural = "Categorias"

    def __str__(self):
        return self.categoria

    def get_absolute_url(self):
        return reverse("produto-detail", args=[self.slug])
