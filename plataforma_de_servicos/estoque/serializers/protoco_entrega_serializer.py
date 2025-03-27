from logging import getLogger

from django.db import transaction
from rest_framework import serializers

from plataforma_de_servicos.estoque.models.protocolo_entrega_itens_model import (
    ProtocoloEntregaItens,
)
from plataforma_de_servicos.estoque.models.protocolo_entrega_model import (
    ProtocoloEntrega,
)
from plataforma_de_servicos.estoque.serializers.inlines.protocolo_itens_inline_serializer import (
    ProtocoloEntregaItensInlineSerializer,
)

log = getLogger("django")


class ProtocoloEntregaGetSerializer(serializers.ModelSerializer):
    protocolo_entrega_itens = ProtocoloEntregaItensInlineSerializer(many=True)

    class Meta:
        fields = "__all__"
        model = ProtocoloEntrega


class ProtocoloEntregaPostSerializer(serializers.ModelSerializer):
    protocolo_entrega_itens = ProtocoloEntregaItensInlineSerializer(many=True)

    class Meta:
        fields = "__all__"
        model = ProtocoloEntrega

    @transaction.atomic
    def create(self, validated_data):
        """
        Recebe os dados validados e cria uma entrada de estoque com os seus itens.
        Receives the validated data and creates a stock entry with its items.
        """
        user = self.context["request"].user
        itens = validated_data.pop("protocolo_entrega_itens")
        protocolo = super().create(validated_data)

        itens = ProtocoloEntregaItens.objects.bulk_create(
            [ProtocoloEntregaItens(estoque=protocolo, **item) for item in itens],
        )
        protocolo.processar_protocolo(user=user)

        return protocolo
