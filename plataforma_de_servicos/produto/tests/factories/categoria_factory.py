import factory
from factory import Faker
from factory.django import DjangoModelFactory

from plataforma_de_servicos.produto.models.categoria_model import Categoria


class CategoriaFactory(DjangoModelFactory):
    class Meta:
        model = Categoria
    
    @factory.lazy_attribute
    def categoria(self):
        instances = [
            "Pizzas Salgadas Tradicionais",
            "Pizzas Salgadas Especiais",
            "Pizzas Doces",
            "Bebidas",
            "Acompanhamentos",
            "Outros",
        ]
        for instance in instances:
            categorias = Categoria.objects.filter(categoria=instance)
            if categorias.exists():
                continue
            return instance
        raise ValueError("Todas as categorias já existem")
        