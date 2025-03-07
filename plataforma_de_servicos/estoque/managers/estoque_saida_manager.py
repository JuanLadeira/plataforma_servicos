from django.db import models


class EstoqueSaidaManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(movimento="s")
