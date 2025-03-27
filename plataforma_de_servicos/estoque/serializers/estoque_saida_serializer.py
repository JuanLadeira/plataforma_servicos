from django.db import transaction
from rest_framework import serializers

from plataforma_de_servicos.estoque.models.estoque_itens_model import EstoqueItens
from plataforma_de_servicos.estoque.models.proxys.estoque_saida import EstoqueSaida
from plataforma_de_servicos.estoque.serializers.inlines.estoque_itens_inline_serializer import (
    EstoqueItensInlineCreateSerializer,
)
from plataforma_de_servicos.estoque.serializers.inlines.estoque_itens_inline_serializer import (
    EstoqueItensInlineGetSerializer,
)


class EstoqueSaidaGetSerializer(serializers.ModelSerializer):
    itens = EstoqueItensInlineGetSerializer(many=True, source="estoque_itens")

    class Meta:
        fields = "__all__"
        model = EstoqueSaida


class EstoqueSaidaPostSerializer(serializers.ModelSerializer):
    itens = EstoqueItensInlineCreateSerializer(many=True, source="estoque_itens")

    class Meta:
        exclude = ["movimento"]
        model = EstoqueSaida

    @transaction.atomic
    def create(self, validated_data):
        """
        Recebe os dados validados e cria uma saida de estoque com os seus itens.
        Receives the validated data and creates a stock out with its items.
        """
        itens_data = validated_data.pop("estoque_itens")
        validated_data["movimento"] = "s"  # Definindo o movimento
        estoque_saida = super().create(validated_data)

        EstoqueItens.objects.bulk_create(
            [
                EstoqueItens(estoque=estoque_saida, **item_data)
                for item_data in itens_data
            ],
        )
        estoque_saida.processar()

        return estoque_saida
