from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.urls import reverse
from django_extensions.db.models import AutoSlugField

from plataforma_de_servicos.produto.models.categoria_model import Categoria


class OrderField(models.PositiveIntegerField):
    def __init__(self, related_field=None, *args, **kwargs):
        self.related_field = related_field
        super().__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        if getattr(model_instance, self.attname) is None:
            # Get the related field value
            related_value = getattr(model_instance, self.related_field) if self.related_field else None

            # Filter by the related field if provided
            queryset = model_instance.__class__.objects
            if related_value:
                queryset = queryset.filter(**{self.related_field: related_value})

            # Get the maximum value of the field in the filtered queryset
            try:
                obj = queryset.latest(self.attname)
                value = getattr(obj, self.attname) + 1
            except ObjectDoesNotExist:
                value = 1

            setattr(model_instance, self.attname, value)
            return value

        return super().pre_save(model_instance, add)


class Image(models.Model):
    image = models.ImageField(upload_to="produtos/")
    produto = models.ForeignKey(
        "Produto",
        on_delete=models.CASCADE,
        related_name="images",
        null=True,
        blank=True,
    )
    order = OrderField(related_field="produto")

    class Meta:
        verbose_name = "Imagem"
        verbose_name_plural = "Imagens"
        ordering = ["order"]

    def __str__(self):
        return f"Produto: {self.produto} - Imagem: {self.id}"


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

    def get_absolute_url(self):
        return reverse("produto-detail", args=[self.slug])

    def get_image(self):
        if self.images.exists():
            return self.images.filter(order=1).first().image.url
        return "static/images/no-image.png"

    def get_images(self):
        if self.images.exists():
            return [image.image.url for image in self.images.all()]
        return None

    def get_stock_range(self):
        return [str(i) for i in range(1, min(self.estoque, 20) + 1)]
