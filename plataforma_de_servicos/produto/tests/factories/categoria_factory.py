import factory
from factory import Faker
from factory.django import DjangoModelFactory

from plataforma_de_servicos.produto.models.categoria_model import Categoria


class CategoriaFactory(DjangoModelFactory):
    class Meta:
        model = Categoria
        django_get_or_create = ('categoria',)
    
    categoria = factory.Iterator([
        "Pizzas Salgadas Tradicionais",
        "Pizzas Salgadas Especiais", 
        "Pizzas Doces",
        "Bebidas",
        "Acompanhamentos",
        "Outros",
    ])
        