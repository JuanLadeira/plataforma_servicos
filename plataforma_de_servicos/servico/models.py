from django.db import models


class StatusServico(models.TextChoices):
    AGUARDANDO_ORCAMENTO = "AGUARDANDO_ORCAMENTO", "Aguardando Orçamento"
    AGUARDANDO_APROVACAO = "AGUARDANDO_APROVACAO", "Aguardando Aprovação"
    EM_FATURAMENTO = "EM_FATURAMENTO", "Em Faturamento"
    FINALIZADO = "FINALIZADO", "Finalizado"
    CANCELADO = "CANCELADO", "Cancelado"


class Servico(models.Model):
    identificador = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    data_entrada = models.DateField()
    aprovacao = models.BooleanField(default=False)
    prazo_entrega = models.IntegerField()
    status_servico = models.CharField(
        max_length=50,
        choices=StatusServico.choices,
    )
    data_da_aprovacao = models.DateField(null=True, blank=True)
    local = models.CharField(max_length=255)

    def __str__(self):
        return super().__str__()


class ItemServico(models.Model):
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE)

    def __str__(self):
        return super().__str__()
