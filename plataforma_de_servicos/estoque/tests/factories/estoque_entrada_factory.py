from django.utils import timezone
from factory import Faker
from factory import SubFactory
from factory.django import DjangoModelFactory

from plataforma_de_servicos.estoque.models.estoque_model import Estoque
from plataforma_de_servicos.users.tests.factories import UserFactory


class EstoqueEntradaFactory(DjangoModelFactory):
    class Meta:
        model = Estoque

    funcionario = SubFactory(UserFactory)
    nf = Faker("random_int", min=1, max=999)
    movimento = "e"
    processado = False
    data = Faker(
        "date_time_this_month",
        before_now=True,
        after_now=False,
        tzinfo=timezone.get_current_timezone(),
    )
