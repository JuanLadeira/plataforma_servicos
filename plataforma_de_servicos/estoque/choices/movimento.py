from django.db import models


class Movimento(models.TextChoices):
    ENTRADA = "e", "Entrada"
    SAIDA = "s", "Saída"
    TRANSFERENCIA = "t", "Transferência"
