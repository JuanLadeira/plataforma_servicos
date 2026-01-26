import factory
from factory.django import DjangoModelFactory

from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.inventario.models import InventarioSaldo


class InventarioFactory(DjangoModelFactory):
    class Meta:
        model = Inventario
        django_get_or_create = ("nome",)

    nome = factory.Faker("company")
    is_ativo = True
    exibir_na_vitrine = False


class InventarioSaldoFactory(DjangoModelFactory):
    class Meta:
        model = InventarioSaldo

    inventario = factory.SubFactory(InventarioFactory)
    quantidade = factory.Faker("random_int", min=1, max=100)
