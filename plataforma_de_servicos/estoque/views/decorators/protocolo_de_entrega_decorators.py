from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import extend_schema

from plataforma_de_servicos.estoque.serializers.protoco_entrega_serializer import (
    ProtocoloEntregaGetSerializer,
)
from plataforma_de_servicos.estoque.serializers.protoco_entrega_serializer import (
    ProtocoloEntregaPostSerializer,
)


def create_protocolo_entrega_schema(view_func):
    decorator = extend_schema(
        tags=["Estoque - protocolo_entrega"],
        summary="""
        Create a stock entry -
        Criar uma protocolo_entrega de estoque
        """,
        description="""
        This endpoint is responsible
        for creating a stock entry.

        The product id must be informed in the 'produto'
        field and the quantity in the 'quantidade' field.
        The data must be sent as a list of JSON objects
        in the 'itens' field.

        Este endpoint é responsável por criar
        um protocolo_entrega de estoque.

        O id do produto deve ser informado
        no campo 'produto' e a quantidade
        no campo 'quantidade'.
        Os dados devem ser enviados como uma
        lista de objetos JSON no campo 'itens'.
        """,
        request=ProtocoloEntregaPostSerializer,
        responses={200: ProtocoloEntregaPostSerializer},
    )
    return decorator(view_func)


def retrieve_protocolo_entrega_schema(view_func):
    decorator = extend_schema(
        tags=["Estoque - protocolo_entrega"],
        summary="Retrieve a protocolo de entrega",
        description="Retrieve a protocolo de entrega by id",
        responses={
            200: ProtocoloEntregaGetSerializer,
            404: {"detail": "Protocolo não encontrado"},
        },
    )
    return decorator(view_func)


def list_protocolo_entrega_schema(view_func):
    decorator = extend_schema(
        tags=["Estoque - protocolo_entrega"],
        summary="""
        List Estoques or
        search for a stock entry by produto
        """,
        description="""List all stock entries or
        search for a stock entry by produto""",
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="""
                List or Search for a
                estoque entry by produto or
                'nota fiscal' (nf)
                """,
                examples=[
                    OpenApiExample(
                        name="""
                        Search by a product name or
                        'nota fiscal' (nf)
                        Buscar protocolo_entrega de estoque
                        por um nome de produto ou
                        'nota fiscal' (nf)
                        """,
                        value="name",
                    ),
                ],
            ),
            OpenApiParameter(
                name="data_protocolo_entrega",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="""
                Filter by entry date
                Filtrar por data de protocolo_entrega
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
