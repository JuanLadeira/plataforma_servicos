from django.db import models
from django_extensions.db.models import AutoSlugField


class Categoria(models.Model):
    categoria = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="categoria", unique=True)

    class Meta:
        ordering = ("categoria",)

    def __str__(self):
        return self.categoria
