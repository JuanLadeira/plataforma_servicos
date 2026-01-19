from django.db import models


class OrigemSaida(models.TextChoices):
    PEDIDO = "pedido", "Pedido/Venda"
    PERDA = "perda", "Perda/Avaria"
    DEVOLUCAO = "devolucao", "Devolução"
    AJUSTE = "ajuste", "Ajuste de Inventário"
    TRANSFERENCIA = "transferencia", "Transferência"
    OUTROS = "outros", "Outros"