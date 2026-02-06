from logging import getLogger

import pytest
from pytest_factoryboy import register
from rest_framework.test import APIClient

from plataforma_de_servicos.corretor.tests.factories import CorretorFactory
from plataforma_de_servicos.corretor.tests.factories import InteresseCompraFactory
from plataforma_de_servicos.corretor.tests.factories import ItemInteresseFactory
from plataforma_de_servicos.estoque.tests.factories.estoque_entrada_factory import (
    EstoqueEntradaFactory,
)
from plataforma_de_servicos.estoque.tests.factories.estoque_itens_factory import (
    EstoqueItensFactory,
)
from plataforma_de_servicos.inventario.tests.factories import InventarioFactory
from plataforma_de_servicos.produto.tests.factories.categoria_factory import (
    CategoriaFactory,
)
from plataforma_de_servicos.produto.tests.factories.produto_factory import (
    ProdutoFactory,
)
from plataforma_de_servicos.users.models import User
from plataforma_de_servicos.users.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def _media_storage(settings, tmpdir) -> None:
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture
def user(db) -> User:
    return UserFactory()


logger = getLogger("django")


@pytest.fixture
def api_client():
    return APIClient()


register(ProdutoFactory)
register(CategoriaFactory)
register(UserFactory)
register(EstoqueEntradaFactory)
register(EstoqueItensFactory)
register(InventarioFactory)
register(CorretorFactory)
register(InteresseCompraFactory)
register(ItemInteresseFactory)
