from decimal import Decimal

import pytest

from plataforma_de_servicos.empresa.tests.factories import EmpresaFactory
from plataforma_de_servicos.estoque.tests import cenarios
from plataforma_de_servicos.users.tests.factories import UserFactory
from plataforma_de_servicos.vendas.models import ConfiguracaoComissao


@pytest.fixture
def empresa():
    """Empresa com comissão padrão de 5%."""
    empresa = EmpresaFactory()
    ConfiguracaoComissao.objects.create(
        empresa=empresa, percentual_padrao=Decimal("5.00")
    )
    return empresa


@pytest.fixture
def padrao(empresa):
    return cenarios.deposito(empresa=empresa, nome="Principal", padrao=True)


@pytest.fixture
def usuario():
    return UserFactory()
