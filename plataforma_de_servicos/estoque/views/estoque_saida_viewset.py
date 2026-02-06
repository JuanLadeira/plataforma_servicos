from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response

from plataforma_de_servicos.core.views import CreateListRetriveModelViewSet
from plataforma_de_servicos.estoque.exceptions import ProdutoSaldoInsuficienteError
from plataforma_de_servicos.estoque.models.proxys.estoque_saida import EstoqueSaida
from plataforma_de_servicos.estoque.serializers.estoque_saida_serializer import (
    EstoqueSaidaGetSerializer,
)
from plataforma_de_servicos.estoque.serializers.estoque_saida_serializer import (
    EstoqueSaidaPostSerializer,
)
from plataforma_de_servicos.estoque.views.decorators.estoque_saida_decorators import (
    create_estoque_saida_schema,
)
from plataforma_de_servicos.estoque.views.decorators.estoque_saida_decorators import (
    list_estoque_saida_schema,
)
from plataforma_de_servicos.estoque.views.decorators.estoque_saida_decorators import (
    retrieve_estoque_saida_schema,
)


class EstoqueSaidaViewSet(CreateListRetriveModelViewSet):
    queryset = EstoqueSaida.objects.all()

    def get_queryset(self):
        """Filtra queryset por tenant."""
        queryset = super().get_queryset()
        tenant = getattr(self.request, "tenant", None)
        if tenant:
            return queryset.filter(empresa=tenant)
        return queryset.none()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return EstoqueSaidaGetSerializer
        return EstoqueSaidaPostSerializer

    def perform_create(self, serializer):
        """Auto-preenche empresa ao criar."""
        tenant = getattr(self.request, "tenant", None)
        serializer.save(empresa=tenant)

    @retrieve_estoque_saida_schema
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a stock out by id.
        Recupera uma saída de estoque pelo id.
        """
        return super().retrieve(request, *args, **kwargs)

    @list_estoque_saida_schema
    def list(self, request, *args, **kwargs):
        """
        List all stock outs or
        search for a estoque entry by product or
        'nota fiscal' (nf)
        Lista todas as saídas de estoque ou
        busca uma saida de estoque por produto ou
        'nota fiscal' (nf)
        """
        search = request.query_params.get("search", None)
        data_saida = request.query_params.get("data_saida", None)
        processado = request.query_params.get("processado", None)
        queryset = self.get_queryset()
        if processado:
            queryset = queryset.filter(processado=processado)
        if data_saida:
            queryset = queryset.filter(data=data_saida)
        if search:
            queryset = queryset.filter(
                Q(estoque_itens__produto__produto=search) | Q(nf=search),
            )
        serializer = EstoqueSaidaGetSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @create_estoque_saida_schema
    def create(self, request, *args, **kwargs):
        """
        Create a stock out.
        Cria uma saída de estoque.
        """
        try:
            return super().create(request, *args, **kwargs)
        except ProdutoSaldoInsuficienteError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
