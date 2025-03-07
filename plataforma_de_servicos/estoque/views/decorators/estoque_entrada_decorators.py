from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import extend_schema

from plataforma_de_servicos.estoque.serializers.estoque_entrada_serializer import (
    EstoqueEntradaGetSerializer,
)
from plataforma_de_servicos.estoque.serializers.estoque_entrada_serializer import (
    EstoqueEntradaPostSerializer,
)


def create_estoque_entrada_schema(view_func):
    decorator = extend_schema(
        tags=["Estoque - Entrada"],
        summary="Create a stock entry - Criar uma entrada de estoque",
        description="""
        This endpoint is responsible for creating a stock entry.
        The product id must be informed in the 'produto'
        field and the quantity in the 'quantidade' field.
        The data must be sent as a list of JSON objects in
        the 'itens' field.

        Este endpoint é responsável por criar uma entrada
          de estoque.

        O id do produto deve ser informado no campo 'produto'
        e a quantidade no campo 'quantidade'.
        Os dados devem ser enviados como uma lista de objetos
        JSON no campo 'itens'.
        """,
        request=EstoqueEntradaPostSerializer,
        responses={200: EstoqueEntradaPostSerializer},
    )
    return decorator(view_func)


def retrieve_estoque_entrada_schema(view_func):
    decorator = extend_schema(
        tags=["Estoque - Entrada"],
        summary="Retrieve a estock entry",
        description="Retrieve a stock by id",
        responses={
            200: EstoqueEntradaGetSerializer,
            404: {"detail": "Estoque não encontrado"},
        },
    )
    return decorator(view_func)


def list_estoque_entrada_schema(view_func):
    decorator = extend_schema(
        tags=["Estoque - Entrada"],
        summary="List Estoques or search for a stock entry by produto",
        description="List all stock entries or search for a stock entry by produto",
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="""
                List or Search for a estoque entry by
                produto or 'nota fiscal' (nf)
                """,
                examples=[
                    OpenApiExample(
                        name="""
                        Search by a product name or 'nota fiscal' (nf)
                        Buscar entrada de estoque por um nome de produto
                        ou 'nota fiscal' (nf)
                        """,
                        value="name",
                    ),
                ],
            ),
            OpenApiParameter(
                name="data_entrada",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="""
                Filter by entry date
                Filtrar por data de entrada
                """,
            ),
            OpenApiParameter(
                name="processado",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="""
                Filter by processed status.
                True: Processed
                False: Not processed

                Filtrar por status de processamento.
                True: Processado
                False: Não processado

                """,
            ),
        ],
    )
    return decorator(view_func)
