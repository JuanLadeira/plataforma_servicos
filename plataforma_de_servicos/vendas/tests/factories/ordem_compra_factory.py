from decimal import Decimal

import factory
from factory import Faker
from factory.django import DjangoModelFactory

from plataforma_de_servicos.corretor.tests.factories import InteresseCompraFactory
from plataforma_de_servicos.empresa.tests.factories import EmpresaFactory
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.users.tests.factories import FuncionarioFactory
from plataforma_de_servicos.vendas.models import ItemOrdemCompra
from plataforma_de_servicos.vendas.models import OrdemCompra
from plataforma_de_servicos.vendas.models import StatusOrdemCompra
from plataforma_de_servicos.vendas.services import OrdemCompraService


class OrdemCompraFactory(DjangoModelFactory):
    class Meta:
        model = OrdemCompra
        skip_postgeneration_save = True

    empresa = factory.SubFactory(EmpresaFactory)
    numero = factory.LazyAttribute(
        lambda o: OrdemCompraService.gerar_numero(o.empresa)
    )
    interesse = factory.SubFactory(InteresseCompraFactory)
    nome_cliente = Faker("name", locale="pt_BR")
    email_cliente = Faker("email")
    telefone_cliente = Faker("phone_number", locale="pt_BR")
    valor_total = Faker("pydecimal", left_digits=3, right_digits=2, positive=True)
    status = StatusOrdemCompra.PENDENTE_APROVACAO

    class Params:
        com_corretor = factory.Trait(
            corretor=factory.SubFactory(FuncionarioFactory, is_corretor=True),
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

    @factory.post_generation
    def deposito_padrao(self, create, extracted, **kwargs):
        """Garante um depósito padrão na empresa da ordem; a aprovação exige um.

        Use OrdemCompraFactory(deposito_padrao=False) para testar a empresa sem padrão.
        """
        if not create or extracted is False or self.empresa_id is None:
            return
        if not Inventario.objects.filter(empresa=self.empresa, padrao=True).exists():
            Inventario.objects.create(empresa=self.empresa, nome="Depósito padrão", padrao=True)


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
