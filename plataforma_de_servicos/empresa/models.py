from django.core.validators import RegexValidator
from django.db import models


class Empresa(models.Model):
    nome = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    email = models.EmailField()
    imo = models.CharField(max_length=100)
    foto = models.ImageField(upload_to="empresas/", blank=True, null=True)

    # Campo para customizar o endpoint do admin da empresa
    admin_url = models.CharField(
        max_length=50,
        default="gerentes",
        validators=[
            RegexValidator(
                regex=r'^[a-z0-9-]+$',
                message='Use apenas letras minúsculas, números e hífens.',
            ),
        ],
        help_text="Endpoint do painel administrativo (ex: 'gerentes' → /gerentes/). "
                  "Use apenas letras minúsculas, números e hífens.",
        verbose_name="URL do Admin",
    )

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def get_admin_url(self):
        """Retorna a URL completa do admin da empresa."""
        return f"/{self.admin_url}/"
