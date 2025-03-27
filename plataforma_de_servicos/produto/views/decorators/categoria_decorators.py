from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import extend_schema

from plataforma_de_servicos.produto.serializers.categoria_serializer import (
    CategoriaGetSerializer,
)
from plataforma_de_servicos.produto.serializers.categoria_serializer import (
    CategoriaPostSerializer,
)


def create_categoria_schema(view_func):
    decorator = extend_schema(
        tags=["Categoria"],
        summary="Create a categoria",
        description="Create a new categoria",
        request=CategoriaPostSerializer,
        responses={200: CategoriaPostSerializer},
    )
    return decorator(view_func)


def update_categoria_schema(view_func):
    decorator = extend_schema(
        tags=["Categoria"],
        summary="Update a categoria",
        description="Update a categoria",
        request=CategoriaPostSerializer,
        responses={200: CategoriaPostSerializer},
    )
    return decorator(view_func)


def partial_update_categoria_schema(view_func):
    decorator = extend_schema(
        tags=["Categoria"],
        summary="Partial update a categoria",
        description="Partial update a categoria",
        request=CategoriaPostSerializer,
        responses={200: CategoriaPostSerializer},
    )
    return decorator(view_func)


def retrieve_categoria_schema(view_func):
    decorator = extend_schema(
        tags=["Categoria"],
        summary="Retrieve a categoria",
        description="Retrieve a categoria by slug",
        responses={200: CategoriaGetSerializer},
    )
    return decorator(view_func)


def list_categoria_schema(view_func):
    decorator = extend_schema(
        tags=["Categoria"],
        summary="List categorias or search for a categoria",
        description="List all categorias or search for a categoria by name",
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="List or Search for a categoria by name",
                examples=[
                    OpenApiExample(
                        name="Search by name",
                        value="name",
                    ),
                ],
            ),
        ],
    )
    return decorator(view_func)


def destroy_categoria_schema(view_func):
    decorator = extend_schema(
        tags=["Categoria"],
        summary="Delete a categoria",
        description="Delete a categoria by slug",
    )
    return decorator(view_func)
