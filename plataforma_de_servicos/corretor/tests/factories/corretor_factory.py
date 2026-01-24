from decimal import Decimal

import factory
from factory import Faker
from factory import LazyAttribute
from factory.django import DjangoModelFactory

from plataforma_de_servicos.corretor.models import Corretor
from plataforma_de_servicos.corretor.models import InteresseCompra
from plataforma_de_servicos.corretor.models import ItemInteresse
from plataforma_de_servicos.users.tests.factories import UserFactory


class CorretorFactory(DjangoModelFactory):
    class Meta:
        model = Corretor

    nome = Faker("name", locale="pt_BR")
    email = Faker("email")
    telefone = Faker("phone_number", locale="pt_BR")
    ativo = True
    user = None

    class Params:
        com_usuario = factory.Trait(
            user=factory.SubFactory(UserFactory),
        )


class InteresseCompraFactory(DjangoModelFactory):
    class Meta:
        model = InteresseCompra

    nome_cliente = Faker("name", locale="pt_BR")
    email_cliente = Faker("email")
    telefone_cliente = Faker("phone_number", locale="pt_BR")
    mensagem = Faker("text", max_nb_chars=200)
    valor_total = Faker("pydecimal", left_digits=3, right_digits=2, positive=True)

    class Params:
        com_corretor = factory.Trait(
            corretor=factory.SubFactory(CorretorFactory),
        )


class ItemInteresseFactory(DjangoModelFactory):
    class Meta:
        model = ItemInteresse

    interesse = factory.SubFactory(InteresseCompraFactory)
    produto_nome = Faker("word")
    variacao_info = ""
    quantidade = Faker("random_int", min=1, max=5)
    preco_unitario = Faker("pydecimal", left_digits=2, right_digits=2, positive=True)
