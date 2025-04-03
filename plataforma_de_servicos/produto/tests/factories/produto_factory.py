import factory

from django.utils import timezone
from factory import Faker, LazyFunction, SubFactory
from factory.django import DjangoModelFactory

from plataforma_de_servicos.produto.models.produto_model import Produto
from plataforma_de_servicos.produto.models.categoria_model import Categoria
from plataforma_de_servicos.produto.tests.factories.categoria_factory import (
    CategoriaFactory,
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
        instances = [
            # Motos
            "Moto Honda CG 160 Start",
            "Moto Yamaha Fazer 250",
            "Moto BMW G 310 GS",
            "Moto Kawasaki Ninja 400",
            "Moto Suzuki GSX-S750",
            "Moto Harley-Davidson Iron 883",
            "Moto Triumph Tiger 900",
            "Moto Ducati Monster 821",
            "Moto KTM Duke 390",
            "Moto Royal Enfield Classic 350",

            # Carros
            "Carro Fiat Uno 1.0",
            "Carro Volkswagen Gol 1.6",
            "Carro Chevrolet Onix LTZ",
            "Carro Renault Kwid Zen",
            "Carro Ford Ka SE 1.5",
            "Carro Hyundai HB20 Comfort Plus",
            "Carro Toyota Corolla Altis Hybrid",
            "Carro Honda Civic Touring",
            "Carro Nissan Versa Advance",
            "Carro Peugeot 208 Griffe",

            # SUVs
            "SUV Toyota Hilux SW4",
            "SUV Jeep Compass Longitude",
            "SUV Hyundai Creta Platinum",
            "SUV Ford EcoSport Titanium",
            "SUV Chevrolet Tracker Premier",
            "SUV Volkswagen T-Cross Highline",
            "SUV Nissan Kicks Exclusive",
            "SUV Honda HR-V EXL",
            "SUV Mitsubishi Outlander Sport",
            "SUV Kia Sportage EX",
        ]
        
        for instance in instances:
            produto = Produto.objects.filter(produto=instance)
            if produto.exists():
                continue
            return instance
    @factory.lazy_attribute
    def categoria(self):
        # Verifica se a categoria já existe
        categorias = Categoria.objects.all()
        if categorias.exists():
            return categorias.order_by("?").first()
        return CategoriaFactory.create()
 
