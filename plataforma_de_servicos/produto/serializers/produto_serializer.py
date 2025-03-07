from rest_framework import serializers

from plataforma_de_servicos.produto.models.categoria_model import Categoria
from plataforma_de_servicos.produto.models.produto_model import Produto
from plataforma_de_servicos.produto.serializers.inlines.categoria_inline_serializer import (
    CategoriaInlineSerializer,
)


class ProdutoGetSerializer(serializers.ModelSerializer):
    categoria = CategoriaInlineSerializer()

    class Meta:
        fields = "__all__"
        model = Produto


class ProdutoPostSerializer(serializers.ModelSerializer):
    categoria = serializers.PrimaryKeyRelatedField(queryset=Categoria.objects.all())

    class Meta:
        fields = "__all__"
        model = Produto
