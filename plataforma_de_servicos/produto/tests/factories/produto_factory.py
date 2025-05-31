import factory

from django.utils import timezone
from factory import Faker, LazyFunction, SubFactory
from factory.django import DjangoModelFactory

from plataforma_de_servicos.produto.models.produto_model import Produto
from plataforma_de_servicos.produto.models.categoria_model import Categoria
from plataforma_de_servicos.produto.tests.factories.categoria_factory import (
    CategoriaFactory,
)
_pizza_salgadas_tradicionais = [
    "Pizza Calabresa", "Pizza Margherita", "Pizza Portuguesa",
    "Pizza Quatro Queijos", "Pizza Frango com Catupiry",
    "Pizza Bacon com Milho", "Pizza Pepperoni", "Pizza Atum",
    "Pizza Napolitana", "Pizza Mussarela",
]
_pizza_salgadas_especiais = [
    "Pizza Parma com Rúcula", "Pizza Cogumelos Trufados",
    "Pizza Camarão com Alho Poró", "Pizza Brócolis com Bacon",
    "Pizza Carne Seca com Requeijão", "Pizza Vegana de Legumes",
    "Pizza Caprese", "Pizza Siciliana", "Pizza Carbonara", "Pizza Mexicana",
]
_pizzas_doces = [
    "Pizza Brigadeiro", "Pizza Chocolate com Morango",
    "Pizza Banana com Canela", "Pizza Romeu e Julieta", "Pizza Prestígio",
]
_bebidas = [
    "Refrigerante Lata 350ml", "Refrigerante 2 Litros",
    "Água Mineral 500ml", "Suco Natural Laranja 300ml", "Cerveja Long Neck",
]
# This combined list will be used by the 'produto' lazy_attribute to pick a name.
_all_products = (
    _pizza_salgadas_tradicionais +
    _pizza_salgadas_especiais +
    _pizzas_doces +
    _bebidas 
)

class ProdutoFactory(DjangoModelFactory):
    class Meta:
        model = Produto

    importado = Faker("boolean")
    ncm = Faker("numerify", text="12345678")  # Exemplo de NCM fixo ou padrão
    preco = Faker("pydecimal", left_digits=4, right_digits=2, positive=True)  # Preço com 2 casas decimais
    estoque = Faker("random_int", min=0, max=2)  # Estoque entre 10 e 100
    estoque_minimo = Faker("random_int", min=1, max=10)  # Estoque mínimo entre 1 e 10
    data = LazyFunction(timezone.now)




    @factory.lazy_attribute
    def produto(self):
        # Select a product name that doesn't exist yet.
        for instance_name in _all_products:
            if not Produto.objects.filter(produto=instance_name).exists():
                return instance_name
        raise ValueError("All pizza products already exist in the database.")


    @factory.lazy_attribute
    def categoria(self):
        # Use the 'produto' field that has already been generated
        # to determine the correct category.
        if self.produto in _pizza_salgadas_tradicionais:
            category_name = "Pizzas Salgadas Tradicionais"
        elif self.produto in _pizza_salgadas_especiais:
            category_name = "Pizzas Salgadas Especiais"
        elif self.produto in _pizzas_doces:
            category_name = "Pizzas Doces"
        elif self.produto in _bebidas:
            category_name = "Bebidas"
        elif self.produto in _acompanhamentos:
            category_name = "Acompanhamentos"
        else:
            category_name = "Outros" # Fallback
        
        categoria = Categoria.objects.filter(categoria=category_name).first()
        if not categoria:
            # If the category does not exist, create it
            categoria = CategoriaFactory.create(categoria=category_name)

        return categoria
