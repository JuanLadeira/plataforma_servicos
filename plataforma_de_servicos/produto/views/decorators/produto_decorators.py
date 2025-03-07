# api_decorators.py
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import extend_schema

from plataforma_de_servicos.produto.serializers.produto_serializer import (
    ProdutoGetSerializer,
)
from plataforma_de_servicos.produto.serializers.produto_serializer import (
    ProdutoPostSerializer,
)


def create_product_schema(view_func):
    decorator = extend_schema(
        tags=["Produto"],
        summary="Create a product",
        description="Create a new product",
        request=ProdutoPostSerializer,
        responses={200: ProdutoPostSerializer},
    )
    return decorator(view_func)


def update_product_schema(view_func):
    decorator = extend_schema(
        tags=["Produto"],
        summary="Update a product",
        description="Update a product",
        request=ProdutoPostSerializer,
        responses={200: ProdutoPostSerializer},
    )
    return decorator(view_func)


def partial_update_product_schema(view_func):
    decorator = extend_schema(
        tags=["Produto"],
        summary="Partial update a product",
        description="Partial update a product",
        request=ProdutoPostSerializer,
        responses={200: ProdutoPostSerializer},
    )
    return decorator(view_func)


def retrieve_product_schema(view_func):
    decorator = extend_schema(
        tags=["Produto"],
        summary="Retrieve a product",
        description="Retrieve a product by slug",
        responses={200: ProdutoGetSerializer},
    )
    return decorator(view_func)


def list_product_schema(view_func):
    decorator = extend_schema(
        tags=["Produto"],
        summary="List products or search for a product",
        description="""
        List all products or
        search for a product by name,
        description or category
        """,
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="""
                List or Search for a product by name,
                description or category
                """,
                examples=[
                    OpenApiExample(
                        name="Search by name",
                        value="name",
                    ),
                    OpenApiExample(
                        name="Search by description",
                        value="description",
                    ),
                    OpenApiExample(
                        name="Search by category",
                        value="category",
                    ),
                ],
            ),
        ],
    )
    return decorator(view_func)


def destroy_product_schema(view_func):
    decorator = extend_schema(
        tags=["Produto"],
        summary="Delete a product",
        description="Delete a product by slug",
    )
    return decorator(view_func)
