from django.db import models


class StatusCarrinho(models.TextChoices):
    CARRINHO = "carrinho", "Carrinho (em construção)"
    AGUARDANDO_PAGAMENTO = "pendente_pagamento", "Aguardando Pagamento"
    PAGO = "pago", "Pago (Em processamento)"
    CONCLUIDO = "concluido", "Concluído"
    CANCELADO = "cancelado", "Cancelado"


class Carrinho(models.Model):
    empresa = models.ForeignKey(
        "empresa.Empresa",
        on_delete=models.CASCADE,
        related_name="carrinhos",
        verbose_name="Empresa",
        null=True,  # Temporary: remove after data migration
        blank=True,
    )
    identificador = models.CharField(max_length=100)
    slug = models.SlugField()
    data_entrada = models.DateField()
    aprovacao = models.BooleanField(default=False)
    prazo_entrega = models.IntegerField()
    status = models.CharField(
        max_length=50,
        choices=StatusCarrinho.choices,
    )
    data_da_aprovacao = models.DateField(null=True, blank=True)
    local = models.CharField(max_length=255)

    class Meta:
        unique_together = [["empresa", "slug"]]

    def __str__(self):
        return super().__str__()


class Item(models.Model):
    carrinho = models.ForeignKey(Carrinho, on_delete=models.CASCADE)

    def __str__(self):
        return super().__str__()
