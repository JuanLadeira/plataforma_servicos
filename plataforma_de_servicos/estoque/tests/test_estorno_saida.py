import pytest
from django.db import IntegrityError

from plataforma_de_servicos.empresa.tests.factories import EmpresaFactory
from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.estoque.models import Estoque
from plataforma_de_servicos.estoque.tests import cenarios

pytestmark = pytest.mark.django_db


@pytest.fixture
def empresa():
    return EmpresaFactory()


@pytest.fixture
def padrao(empresa):
    return cenarios.deposito(empresa=empresa, nome="Principal", padrao=True)


def test_banco_recusa_dois_estornos_da_mesma_saida(empresa, padrao):
    v = cenarios.variacao_com_saldo({padrao: 5}, empresa=empresa)
    saida = cenarios.saida([(v, 2)], origem=padrao)
    Estoque.objects.create(
        empresa=empresa,
        movimento=Movimento.ENTRADA.value,
        inventario_destino=padrao,
        estorno_de=saida,
    )
    with pytest.raises(IntegrityError):
        Estoque.objects.create(
            empresa=empresa,
            movimento=Movimento.ENTRADA.value,
            inventario_destino=padrao,
            estorno_de=saida,
        )
