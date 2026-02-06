from django.db.models import Q
from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response

from plataforma_de_servicos.produto.models.produto_model import Produto
from plataforma_de_servicos.produto.serializers.produto_serializer import (
    ProdutoGetSerializer,
)
from plataforma_de_servicos.produto.serializers.produto_serializer import (
    ProdutoPostSerializer,
)
from plataforma_de_servicos.produto.views.decorators.produto_decorators import (
    create_product_schema,
)
from plataforma_de_servicos.produto.views.decorators.produto_decorators import (
    destroy_product_schema,
)
from plataforma_de_servicos.produto.views.decorators.produto_decorators import (
    list_product_schema,
)
from plataforma_de_servicos.produto.views.decorators.produto_decorators import (
    partial_update_product_schema,
)
from plataforma_de_servicos.produto.views.decorators.produto_decorators import (
    retrieve_product_schema,
)
from plataforma_de_servicos.produto.views.decorators.produto_decorators import (
    update_product_schema,
)


class ProdutoViewSet(viewsets.ModelViewSet):
    queryset = Produto.objects.all()
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
            return ProdutoGetSerializer
        return ProdutoPostSerializer

    def perform_create(self, serializer):
        """Auto-preenche empresa ao criar."""
        tenant = getattr(self.request, "tenant", None)
        serializer.save(empresa=tenant)

    @retrieve_product_schema
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @list_product_schema
    def list(self, request, *args, **kwargs):
        search = request.query_params.get("search", None)
        queryset = self.get_queryset()
        if search:
            queryset = queryset.filter(
                Q(produto__icontains=search)
                | Q(categoria__categoria__icontains=search),
            )
        serializer = ProdutoGetSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @create_product_schema
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @update_product_schema
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @partial_update_product_schema
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @destroy_product_schema
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
