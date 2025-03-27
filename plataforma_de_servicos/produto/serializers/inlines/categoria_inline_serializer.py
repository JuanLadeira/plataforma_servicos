from rest_framework import serializers

from plataforma_de_servicos.produto.models.categoria_model import Categoria


class CategoriaInlineSerializer(serializers.ModelSerializer):
    class Meta:
        fields = "__all__"
        model = Categoria
