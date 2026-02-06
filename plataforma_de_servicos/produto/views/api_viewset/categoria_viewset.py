from django.db.models import Q
from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response

from plataforma_de_servicos.produto.models.categoria_model import Categoria
from plataforma_de_servicos.produto.serializers.categoria_serializer import (
    CategoriaGetSerializer,
)
from plataforma_de_servicos.produto.serializers.categoria_serializer import (
    CategoriaPostSerializer,
)
from plataforma_de_servicos.produto.views.decorators.categoria_decorators import (
    create_categoria_schema,
)
from plataforma_de_servicos.produto.views.decorators.categoria_decorators import (
    destroy_categoria_schema,
)
from plataforma_de_servicos.produto.views.decorators.categoria_decorators import (
    list_categoria_schema,
)
from plataforma_de_servicos.produto.views.decorators.categoria_decorators import (
    partial_update_categoria_schema,
)
from plataforma_de_servicos.produto.views.decorators.categoria_decorators import (
    retrieve_categoria_schema,
)
from plataforma_de_servicos.produto.views.decorators.categoria_decorators import (
    update_categoria_schema,
)


class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    lookup_field = "slug"

    def get_queryset(self):
        """Filtra queryset por tenant."""
        queryset = super().get_queryset()
        tenant = getattr(self.request, "tenant", None)
        if tenant:
            return queryset.filter(empresa=tenant)
        return queryset.none()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return CategoriaGetSerializer
        return CategoriaPostSerializer

    def perform_create(self, serializer):
        """Auto-preenche empresa ao criar."""
        tenant = getattr(self.request, "tenant", None)
        serializer.save(empresa=tenant)

    @retrieve_categoria_schema
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @list_categoria_schema
    def list(self, request, *args, **kwargs):
        search = request.query_params.get("search", None)
        queryset = self.get_queryset()
        if search:
            queryset = queryset.filter(Q(categoria__icontains=search))
        serializer = CategoriaGetSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @create_categoria_schema
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @update_categoria_schema
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @partial_update_categoria_schema
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @destroy_categoria_schema
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
