import factory
from factory import Faker
from factory.django import DjangoModelFactory

from plataforma_de_servicos.empresa.models import Empresa


class EmpresaFactory(DjangoModelFactory):
    class Meta:
        model = Empresa

    nome = Faker("company", locale="pt_BR")
    slug = factory.Sequence(lambda n: f"empresa-{n}")
    email = Faker("company_email")
    imo = Faker("numerify", text="######")
