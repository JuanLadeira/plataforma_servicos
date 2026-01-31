from django.db import models


class TimeStampedModel(models.Model):
    created = models.DateTimeField(
        "criado em",
        auto_now_add=True,
        auto_now=False,
    )
    modified = models.DateTimeField(
        "modificado em",
        auto_now_add=False,
        auto_now=True,
    )

    class Meta:
        abstract = True


class SiteConfig(TimeStampedModel):
    """
    Configurações do site editáveis via admin.
    Modelo singleton - apenas uma instância deve existir.
    """

    site_name = models.CharField(
        "Nome do Site",
        max_length=100,
        default="AutoPrime",
        help_text="Título exibido no navbar",
    )
    hero_title = models.CharField(
        "Título do Banner",
        max_length=200,
        default="Veículos e Imóveis Premium",
    )
    hero_description = models.TextField(
        "Descrição do Banner",
        default="Encontre carros, motos e imóveis selecionados com as melhores condições do mercado.",
    )
    hero_button_text = models.CharField(
        "Texto do Botão",
        max_length=50,
        default="Ver Ofertas",
    )
    hero_image = models.ImageField(
        "Imagem do Banner",
        upload_to="site/",
        blank=True,
        null=True,
        help_text="Upload de imagem para o banner. Se não fornecida, usa a URL abaixo.",
    )
    hero_image_url = models.URLField(
        "URL da Imagem do Banner",
        blank=True,
        default="https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?q=80&w=2083&auto=format&fit=crop",
        help_text="URL externa para imagem do banner (usada se não houver upload)",
    )

    class Meta:
        verbose_name = "Configuração do Site"
        verbose_name_plural = "Configurações do Site"

    def __str__(self):
        return "Configurações do Site"

    def save(self, *args, **kwargs):
        # Garante que só exista uma instância (singleton)
        if not self.pk and SiteConfig.objects.exists():
            existing = SiteConfig.objects.first()
            self.pk = existing.pk
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        """Retorna a configuração do site, criando se não existir."""
        config, _ = cls.objects.get_or_create(pk=1)
        return config

    def get_hero_image_url(self):
        """Retorna a URL da imagem do hero (upload tem prioridade)."""
        if self.hero_image:
            return self.hero_image.url
        return self.hero_image_url
