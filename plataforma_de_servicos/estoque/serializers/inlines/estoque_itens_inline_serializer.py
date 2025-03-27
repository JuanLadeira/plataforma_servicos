from rest_framework import serializers

from plataforma_de_servicos.estoque.models.estoque_itens_model import EstoqueItens


class EstoqueItensInlineCreateSerializer(serializers.ModelSerializer):
    class Meta:
        exclude = ["estoque", "saldo"]
        model = EstoqueItens

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["saldo"] = instance.saldo
        return data


class EstoqueItensInlineGetSerializer(serializers.ModelSerializer):
    class Meta:
        fields = "__all__"
        model = EstoqueItens
        depth = 1
