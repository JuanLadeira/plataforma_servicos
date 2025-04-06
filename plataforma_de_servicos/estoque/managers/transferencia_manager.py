from django.db import models


class TransferenciaManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(movimento="t")
