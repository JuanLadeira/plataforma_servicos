from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response

from plataforma_de_servicos.core.views import CreateListRetriveModelViewSet
from plataforma_de_servicos.estoque.models.proxys.estoque_entrada import EstoqueEntrada
from plataforma_de_servicos.estoque.serializers.estoque_entrada_serializer import (
    EstoqueEntradaGetSerializer,
)
from plataforma_de_servicos.estoque.serializers.estoque_entrada_serializer import (
    EstoqueEntradaPostSerializer,
)
from plataforma_de_servicos.estoque.views.decorators.estoque_entrada_decorators import (
    create_estoque_entrada_schema,
)
from plataforma_de_servicos.estoque.views.decorators.estoque_entrada_decorators import (
    list_estoque_entrada_schema,
)
from plataforma_de_servicos.estoque.views.decorators.estoque_entrada_decorators import (
    retrieve_estoque_entrada_schema,
)


class EstoqueEntradaViewSet(CreateListRetriveModelViewSet):
    queryset = EstoqueEntrada.objects.all()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return EstoqueEntradaGetSerializer
        return EstoqueEntradaPostSerializer

    @retrieve_estoque_entrada_schema
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a stock entry by id.
        Recupera uma entrada de estoque pelo id.
        """
        return super().retrieve(request, *args, **kwargs)

    @list_estoque_entrada_schema
    def list(self, request, *args, **kwargs):
        """
        List all estoque entries or
        search for a estoque entry by product or
        'nota fiscal' (nf)
        Lista todas as entradas de estoque ou
        busca uma entrada de estoque por produto ou
        'nota fiscal' (nf)
        """
        search = request.query_params.get("search", None)
        data_entrada = request.query_params.get("data_entrada", None)
        processado = request.query_params.get("processado", None)
        queryset = self.get_queryset()
        if processado:
            queryset = queryset.filter(processado=processado)
        if data_entrada:
            queryset = queryset.filter(data=data_entrada)
        if search:
            queryset = queryset.filter(
                Q(estoque_itens__produto__produto=search) | Q(nf=search),
            )
        serializer = EstoqueEntradaGetSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @create_estoque_entrada_schema
    def create(self, request, *args, **kwargs):
        """
        Create a stock entry.
        Cria uma entrada de estoque.
        """
        return super().create(request, *args, **kwargs)
