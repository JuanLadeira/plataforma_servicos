from factory import Faker
from factory.django import DjangoModelFactory

from plataforma_de_servicos.produto.models.categoria_model import Categoria


class CategoriaFactory(DjangoModelFactory):
    class Meta:
        model = Categoria

    categoria = Faker("word")
