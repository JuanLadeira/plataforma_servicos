from django.db import models
from django.db import transaction

from plataforma_de_servicos.core.models import TimeStampedModel
from plataforma_de_servicos.estoque.exceptions import ProtocoloProcessadoError
from plataforma_de_servicos.estoque.models.estoque_itens_model import EstoqueItens
from plataforma_de_servicos.estoque.models.proxys.estoque_saida import EstoqueSaida
from plataforma_de_servicos.users.models import User


class ProtocoloEntrega(TimeStampedModel):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    estoque_atualizado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "protocolo de entrega"
        verbose_name_plural = "protocolos de entrega"

    def __str__(self):
        return str(self.pk)

    def processar_protocolo(self, usuario: User):
        if self.estoque_atualizado:
            raise ProtocoloProcessadoError

        with transaction.atomic():
            # Criar um EstoqueSaida
            estoque_saida = EstoqueSaida.objects.create(
                funcionario=usuario,
                movimento="s",
            )
            for item in self.protocolo_entrega_itens.all():
                # Criar um Estoque Saida Detail
                EstoqueItens.objects.create(
                    estoque=estoque_saida,
                    produto=item.produto,
                    quantidade=item.quantidade,
                )
            # Processando a saida.
            estoque_saida.processar()

            self.estoque_atualizado = True
            self.save()
