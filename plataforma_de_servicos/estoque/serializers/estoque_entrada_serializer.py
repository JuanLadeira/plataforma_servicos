from django.db import transaction
from rest_framework import serializers

from plataforma_de_servicos.estoque.models.estoque_itens_model import EstoqueItens
from plataforma_de_servicos.estoque.models.proxys.estoque_entrada import EstoqueEntrada
from plataforma_de_servicos.estoque.serializers.inlines.estoque_itens_inline_serializer import (
    EstoqueItensInlineCreateSerializer,
)
from plataforma_de_servicos.estoque.serializers.inlines.estoque_itens_inline_serializer import (
    EstoqueItensInlineGetSerializer,
)


class EstoqueEntradaGetSerializer(serializers.ModelSerializer):
    itens = EstoqueItensInlineGetSerializer(
        many=True, source="estoque_itens", required=True,
    )

    class Meta:
        fields = "__all__"
        model = EstoqueEntrada


class EstoqueEntradaPostSerializer(serializers.ModelSerializer):
    itens = EstoqueItensInlineCreateSerializer(
        many=True, source="estoque_itens", required=True,
    )

    class Meta:
        exclude = ["movimento"]
        model = EstoqueEntrada

    @transaction.atomic
    def create(self, validated_data):
        """
        Recebe os dados validados e cria uma entrada de estoque com os seus itens.
        Receives the validated data and creates a stock entry with its items.
        """
        itens_data = validated_data.pop("estoque_itens")
        validated_data["movimento"] = "e"  # Definindo o movimento
        estoque_entrada = super().create(validated_data)

        EstoqueItens.objects.bulk_create(
            [
                EstoqueItens(estoque=estoque_entrada, **item_data)
                for item_data in itens_data
            ],
        )

        estoque_entrada.processar()

        return estoque_entrada
