from rest_framework import serializers

from plataforma_de_servicos.produto.models.produto_model import Produto


class ProdutosInlineSerializer(serializers.ModelSerializer):
    class Meta:
        fields = [
            "pk",
            "importado",
            "ncm",
            "produto",
            "preco",
            "estoque",
            "estoque_minimo",
            "data",
        ]
        model = Produto
