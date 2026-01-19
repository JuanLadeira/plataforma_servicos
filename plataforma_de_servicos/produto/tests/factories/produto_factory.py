import factory
from django.utils import timezone
from factory import Faker
from factory import LazyFunction
from factory.django import DjangoModelFactory

from plataforma_de_servicos.produto.models.categoria_model import Categoria
from plataforma_de_servicos.produto.models.produto_model import Produto
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
_acompanhamentos = []
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
    estoque_minimo = Faker("random_int", min=1, max=10)  # Estoque mínimo entre 1 e 10
    data = LazyFunction(timezone.now)
    categoria = factory.SubFactory(CategoriaFactory)

    @factory.lazy_attribute 
    def produto(self):
        # Otimização: buscar todos os produtos existentes de uma vez
        # em vez de fazer uma query por produto  
        existing_produtos = set(
            Produto.objects.values_list('produto', flat=True)
        )
        
        # Select a product name that doesn't exist yet.
        for instance_name in _all_products:
            if instance_name not in existing_produtos:
                return instance_name
        
        # Fallback: usar timestamp para garantir unicidade
        import time
        return f"Produto-Test-{int(time.time() * 1000000) % 1000000}"
