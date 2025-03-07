from django.db import models

# Create your models here.


class Empresa(models.Model):
    nome = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    email = models.EmailField()
    imo = models.CharField(max_length=100)
    foto = models.ImageField(upload_to="empresas/")

    def __str__(self):
        return self.nome
