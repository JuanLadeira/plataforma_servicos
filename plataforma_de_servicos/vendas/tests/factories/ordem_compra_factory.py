from decimal import Decimal

import factory
from factory import Faker
from factory.django import DjangoModelFactory

from plataforma_de_servicos.corretor.tests.factories import CorretorFactory
from plataforma_de_servicos.corretor.tests.factories import InteresseCompraFactory
from plataforma_de_servicos.vendas.models import ItemOrdemCompra
from plataforma_de_servicos.vendas.models import OrdemCompra
from plataforma_de_servicos.vendas.models import StatusOrdemCompra
from plataforma_de_servicos.vendas.services import OrdemCompraService


class OrdemCompraFactory(DjangoModelFactory):
    class Meta:
        model = OrdemCompra

    numero = factory.LazyFunction(OrdemCompraService.gerar_numero)
    interesse = factory.SubFactory(InteresseCompraFactory)
    nome_cliente = Faker("name", locale="pt_BR")
    email_cliente = Faker("email")
    telefone_cliente = Faker("phone_number", locale="pt_BR")
    valor_total = Faker("pydecimal", left_digits=3, right_digits=2, positive=True)
    status = StatusOrdemCompra.PENDENTE_APROVACAO

    class Params:
        com_corretor = factory.Trait(
            corretor=factory.SubFactory(CorretorFactory),
        )
        aprovada = factory.Trait(
            status=StatusOrdemCompra.APROVADA,
        )
        rejeitada = factory.Trait(
            status=StatusOrdemCompra.REJEITADA,
            motivo_rejeicao="Motivo de teste",
        )
        faturada = factory.Trait(
            status=StatusOrdemCompra.FATURADA,
        )


class ItemOrdemCompraFactory(DjangoModelFactory):
    class Meta:
        model = ItemOrdemCompra

    ordem = factory.SubFactory(OrdemCompraFactory)
    produto = None
    variacao = None
    produto_nome = Faker("word")
    variacao_info = ""
    quantidade = Faker("random_int", min=1, max=5)
    preco_unitario = Faker("pydecimal", left_digits=2, right_digits=2, positive=True)
