import pytest

from pytest_factoryboy import register
from rest_framework.test import APIClient

from plataforma_de_servicos.users.models import User
from plataforma_de_servicos.users.tests.factories import UserFactory
from plataforma_de_servicos.produto.tests.factories.produto_factory import ProdutoFactory
from plataforma_de_servicos.produto.tests.factories.categoria_factory import CategoriaFactory
from plataforma_de_servicos.estoque.tests.factories.estoque_entrada_factory import EstoqueEntradaFactory
from plataforma_de_servicos.estoque.tests.factories.estoque_itens_factory import EstoqueItensFactory


@pytest.fixture(autouse=True)
def _media_storage(settings, tmpdir) -> None:
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture
def user(db) -> User:
    return UserFactory()
from logging import getLogger

logger = getLogger("django")


@pytest.fixture()
def api_client():
    return APIClient()


register(ProdutoFactory)
register(CategoriaFactory)
register(UserFactory)
register(EstoqueEntradaFactory)
register(EstoqueItensFactory)


@pytest.fixture(autouse=True)
def _media_storage(settings, tmpdir) -> None:
    settings.MEDIA_ROOT = tmpdir.strpath