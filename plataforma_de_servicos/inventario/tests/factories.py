import factory
from factory.django import DjangoModelFactory

from plataforma_de_servicos.inventario.models import Inventario


class InventarioFactory(DjangoModelFactory):
    class Meta:
        model = Inventario
        django_get_or_create = ("nome",)

    nome = factory.Faker("company")
