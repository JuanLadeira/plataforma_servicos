import pytest

from plataforma_de_servicos.estoque.serializers.estoque_entrada_serializer import (
    EstoqueEntradaPostSerializer,
)


@pytest.mark.django_db(transaction=True)
class TestEstoqueEntrada:
    def test_estoque_entrada(
        self,
        estoque_entrada_factory,
        estoque_itens_factory,
        produto_factory,
        user_factory,
        inventario_factory,
    ):
        produto = produto_factory(estoque=0)
        produto_2 = produto_factory(estoque=0)
        funcionario = user_factory()
        inventario = inventario_factory()
        dados_entrada = {
            "nf": 1,
            "movimento": "e",
            "funcionario": funcionario.pk,
            "inventario_destino": inventario.pk,
            "itens": [
                {
                    "produto": produto.pk,
                    "quantidade": 1,
                    "inventario": inventario.pk,
                },
                {
                    "produto": produto_2.pk,
                    "quantidade": 2,
                    "inventario": inventario.pk,
                },
            ],
        }

        # Usar o serializer
        estoque_entrada_serializer_class = EstoqueEntradaPostSerializer
        serializer = estoque_entrada_serializer_class(data=dados_entrada)
        assert serializer.is_valid(raise_exception=True)
        estoque_entrada = serializer.save()
        produto_2.refresh_from_db()
        produto.refresh_from_db()
        itens = estoque_entrada.estoque_itens.all()
        dois = 2
        um = 1
        assert itens.count() == dois

        produto_1 = estoque_entrada.estoque_itens.first().produto
        item_1 = estoque_entrada.estoque_itens.first()
        # Verificar os resultados
        assert estoque_entrada.pk is not None
        assert estoque_entrada.nf == dados_entrada["nf"]
        assert estoque_entrada.movimento == dados_entrada["movimento"]
        assert estoque_entrada.estoque_itens.count() == dois
        assert item_1.quantidade == um
        assert produto_1.pk == produto.pk
        assert produto_1.estoque == um
        assert produto_2.estoque == dois
