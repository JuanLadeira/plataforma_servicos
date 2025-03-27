from django.db.models import Q
from django.db.models import Value
from django.db.models.functions import Concat
from rest_framework import status
from rest_framework.response import Response

from plataforma_de_servicos.core.views import CreateListRetriveModelViewSet
from plataforma_de_servicos.estoque.exceptions import ProdutoSaldoInsuficienteError
from plataforma_de_servicos.estoque.exceptions import ProtocoloProcessadoError
from plataforma_de_servicos.estoque.models.protocolo_entrega_model import (
    ProtocoloEntrega,
)
from plataforma_de_servicos.estoque.serializers.protoco_entrega_serializer import (
    ProtocoloEntregaGetSerializer,
)
from plataforma_de_servicos.estoque.serializers.protoco_entrega_serializer import (
    ProtocoloEntregaPostSerializer,
)
from plataforma_de_servicos.estoque.views.decorators.protocolo_de_entrega_decorators import (
    create_protocolo_entrega_schema,
)
from plataforma_de_servicos.estoque.views.decorators.protocolo_de_entrega_decorators import (
    list_protocolo_entrega_schema,
)
from plataforma_de_servicos.estoque.views.decorators.protocolo_de_entrega_decorators import (
    retrieve_protocolo_entrega_schema,
)


class ProtocoloEntregaViewSet(CreateListRetriveModelViewSet):
    queryset = ProtocoloEntrega.objects.all()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ProtocoloEntregaGetSerializer
        return ProtocoloEntregaPostSerializer

    @retrieve_protocolo_entrega_schema
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a delivery protocol by id.
        Recupera um protocolo de entrega pelo id.
        """
        return super().retrieve(request, *args, **kwargs)

    @list_protocolo_entrega_schema
    def list(self, request, *args, **kwargs):
        """
        List all deliveries protocols or
        search for a delivery by product name
        or user who was responsible for the delivery.
        Lista todos os protocolos de entrega ou
        busca um protocolo de entrega pelo nome do produto
        ou usuário responsável pela entrega.
        """
        search = request.query_params.get("search", None)
        created = request.query_params.get("data", None)
        queryset = self.get_queryset()
        if created:
            queryset = queryset.filter(created=created)
        if search:
            queryset = queryset.annotate(
                full_name=Concat(
                    "usuario__first_name", Value(" "), "usuario__last_name",
                ),
            )
            queryset = queryset.filter(
                Q(estoque_itens__produto__produto=search)
                | Q(full_name__icontains=search),
            )
        serializer = ProtocoloEntregaGetSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @create_protocolo_entrega_schema
    def create(self, request, *args, **kwargs):
        """
        Create a delivery protocol.
        Cria um protocolo de entrega.
        """
        try:
            return super().create(request, *args, **kwargs)
        except ProdutoSaldoInsuficienteError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except ProtocoloProcessadoError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
