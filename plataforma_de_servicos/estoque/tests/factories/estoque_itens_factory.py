from factory import Faker
from factory import SubFactory
from factory.django import DjangoModelFactory

from plataforma_de_servicos.estoque.models.estoque_itens_model import EstoqueItens
from plataforma_de_servicos.produto.tests.factories.produto_factory import (
    ProdutoFactory,
)


class EstoqueItensFactory(DjangoModelFactory):
    class Meta:
        model = EstoqueItens

    quantidade = Faker("random_int", min=1, max=999)
    produto = SubFactory(ProdutoFactory)
    saldo = 0
