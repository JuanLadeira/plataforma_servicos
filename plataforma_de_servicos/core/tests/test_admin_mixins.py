"""
Testes para o TenantAwareAdminMixin e a lógica de isolamento de dados.
"""
import pytest
from django.contrib.admin import ModelAdmin
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from plataforma_de_servicos.core.admin.mixins import TenantAwareAdminMixin
from plataforma_de_servicos.empresa.tests.factories.empresa_factory import EmpresaFactory
from plataforma_de_servicos.produto.models import Categoria, Produto
from plataforma_de_servicos.produto.tests.factories.categoria_factory import (
    CategoriaFactory,
)
from plataforma_de_servicos.produto.tests.factories.produto_factory import ProdutoFactory
from plataforma_de_servicos.users.tests.factories import FuncionarioFactory

User = get_user_model()


@pytest.fixture
def empresa_a():
    return EmpresaFactory(nome="Empresa A")


@pytest.fixture
def empresa_b():
    return EmpresaFactory(nome="Empresa B")


@pytest.fixture
def user_a(empresa_a):
    return FuncionarioFactory(empresa=empresa_a).usuario


@pytest.fixture
def user_b(empresa_b):
    return FuncionarioFactory(empresa=empresa_b).usuario


@pytest.fixture
def categoria_a(empresa_a):
    return CategoriaFactory(empresa=empresa_a, categoria="Categoria A")


@pytest.fixture
def categoria_b(empresa_b):
    return CategoriaFactory(empresa=empresa_b, categoria="Categoria B")


@pytest.fixture
def produto_a(categoria_a):
    return ProdutoFactory(
        produto="Produto A", categoria=categoria_a, empresa=categoria_a.empresa
    )


@pytest.fixture
def produto_b(categoria_b):
    return ProdutoFactory(
        produto="Produto B", categoria=categoria_b, empresa=categoria_b.empresa
    )


@pytest.mark.django_db
class TestTenantAwareAdminMixin:
    def test_queryset_is_isolated_for_tenant(
        self, user_a, empresa_a, produto_a, produto_b
    ):
        """
        Verifica se o queryset do admin é filtrado corretamente para o tenant do usuário.
        """
        # Arrange
        request = RequestFactory().get("/admin/produto/produto/")
        request.user = user_a
        request.tenant = empresa_a

        # Define um ModelAdmin simples com o mixin para o teste
        class ProdutoAdmin(TenantAwareAdminMixin, ModelAdmin):
            model = Produto

        admin_instance = ProdutoAdmin(Produto, None)

        # Act
        qs = admin_instance.get_queryset(request)

        # Assert
        assert qs.count() == 1
        assert qs.first() == produto_a
        assert produto_b not in qs

    def test_formfield_for_foreignkey_is_isolated(
        self, user_a, empresa_a, categoria_a, categoria_b
    ):
        """
        Verifica se as opções de ForeignKey (ex: Categoria) são filtradas
        para o tenant do usuário.
        """
        # Arrange
        request = RequestFactory().get("/admin/produto/produto/add/")
        request.user = user_a
        request.tenant = empresa_a

        class ProdutoAdmin(TenantAwareAdminMixin, ModelAdmin):
            model = Produto

        admin_instance = ProdutoAdmin(Produto, None)
        db_field = Produto._meta.get_field("categoria")

        # Act
        formfield = admin_instance.formfield_for_foreignkey(db_field, request)
        qs = formfield.queryset

        # Assert
        assert qs.count() == 1
        assert qs.first() == categoria_a
        assert categoria_b not in qs

    def test_save_model_assigns_correct_tenant(self, user_a, empresa_a, categoria_a):
        """
        Verifica se o mixin atribui a empresa correta ao salvar um novo objeto.
        """
        # Arrange
        request = RequestFactory().post("/admin/produto/produto/add/")
        request.user = user_a
        request.tenant = empresa_a

        class ProdutoAdmin(TenantAwareAdminMixin, ModelAdmin):
            model = Produto

        admin_instance = ProdutoAdmin(Produto, None)
        new_produto = Produto(produto="Novo Produto", categoria=categoria_a)

        # Act
        admin_instance.save_model(request, new_produto, None, change=False)

        # Assert
        assert new_produto.empresa == empresa_a
        assert new_produto.pk is not None  # Garante que o objeto foi salvo
