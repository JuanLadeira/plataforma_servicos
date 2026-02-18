"""
Testes de acesso ao admin com isolamento de tenant.

Verifica que funcionários só podem acessar o admin da sua própria empresa
e que dados são corretamente isolados entre tenants.
"""
import pytest
from django.test import Client, RequestFactory

from plataforma_de_servicos.core.admin.sites.gerente_admin_site import gerente_site
from plataforma_de_servicos.empresa.tests.factories.empresa_factory import EmpresaFactory
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.produto.models import Produto, Categoria
from plataforma_de_servicos.users.models import Funcionario, User
from plataforma_de_servicos.users.tests.factories import FuncionarioFactory, UserFactory


@pytest.fixture
def empresa_autoprime(db):
    """Empresa AutoPrime para testes."""
    return EmpresaFactory(nome="AutoPrime", slug="autoprime")


@pytest.fixture
def empresa_autolitros(db):
    """Empresa AutoLitros para testes."""
    return EmpresaFactory(nome="AutoLitros", slug="autolitros")


@pytest.fixture
def funcionario_autoprime(empresa_autoprime):
    """Funcionário da empresa AutoPrime."""
    user = UserFactory(email="gerente@autoprime.com")
    return FuncionarioFactory(usuario=user, empresa=empresa_autoprime)


@pytest.fixture
def funcionario_autolitros(empresa_autolitros):
    """Funcionário da empresa AutoLitros."""
    user = UserFactory(email="gerente@autolitros.com")
    return FuncionarioFactory(usuario=user, empresa=empresa_autolitros)


@pytest.fixture
def funcionario_sem_empresa():
    """Funcionário sem empresa associada."""
    user = UserFactory(email="orfao@teste.com")
    return FuncionarioFactory(usuario=user, empresa=None)


@pytest.fixture
def superuser(db):
    """Superusuário para testes."""
    return User.objects.create_superuser(
        email="super@admin.com",
        password="password123",
    )


@pytest.fixture
def categoria_autoprime(empresa_autoprime):
    """Categoria da empresa AutoPrime."""
    return Categoria.objects.create(
        categoria="Peças AutoPrime",
        empresa=empresa_autoprime,
    )


@pytest.fixture
def categoria_autolitros(empresa_autolitros):
    """Categoria da empresa AutoLitros."""
    return Categoria.objects.create(
        categoria="Óleos AutoLitros",
        empresa=empresa_autolitros,
    )


@pytest.fixture
def produto_autoprime(categoria_autoprime, empresa_autoprime):
    """Produto da empresa AutoPrime."""
    return Produto.objects.create(
        produto="Filtro de Ar",
        preco=50.00,
        categoria=categoria_autoprime,
        empresa=empresa_autoprime,
    )


@pytest.fixture
def produto_autolitros(categoria_autolitros, empresa_autolitros):
    """Produto da empresa AutoLitros."""
    return Produto.objects.create(
        produto="Óleo 5W30",
        preco=80.00,
        categoria=categoria_autolitros,
        empresa=empresa_autolitros,
    )


@pytest.fixture
def inventario_autoprime(empresa_autoprime):
    """Inventário da empresa AutoPrime."""
    return Inventario.objects.create(
        nome="Estoque Principal AutoPrime",
        empresa=empresa_autoprime,
    )


@pytest.fixture
def inventario_autolitros(empresa_autolitros):
    """Inventário da empresa AutoLitros."""
    return Inventario.objects.create(
        nome="Estoque Principal AutoLitros",
        empresa=empresa_autolitros,
    )


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
class TestGerenteAdminHasPermission:
    """Testes de permissão de acesso ao GerenteAdminSite."""

    def test_funcionario_with_empresa_has_permission(
        self, funcionario_autoprime, request_factory
    ):
        """Funcionário com empresa associada tem permissão."""
        request = request_factory.get("/gerentes/")
        request.user = funcionario_autoprime.usuario

        assert gerente_site.has_permission(request) is True

    def test_funcionario_without_empresa_denied(
        self, funcionario_sem_empresa, request_factory
    ):
        """Funcionário sem empresa NÃO tem permissão."""
        request = request_factory.get("/gerentes/")
        request.user = funcionario_sem_empresa.usuario

        assert gerente_site.has_permission(request) is False

    def test_superuser_always_has_permission(
        self, superuser, request_factory
    ):
        """Superusuário sempre tem permissão."""
        request = request_factory.get("/gerentes/")
        request.user = superuser

        assert gerente_site.has_permission(request) is True

    def test_anonymous_user_denied(self, request_factory):
        """Usuário anônimo não tem permissão."""
        from django.contrib.auth.models import AnonymousUser

        request = request_factory.get("/gerentes/")
        request.user = AnonymousUser()

        assert gerente_site.has_permission(request) is False

    def test_regular_user_without_funcionario_denied(
        self, request_factory
    ):
        """Usuário comum sem perfil de funcionário não tem permissão."""
        user = UserFactory()  # Sem perfil de funcionário

        request = request_factory.get("/gerentes/")
        request.user = user

        assert gerente_site.has_permission(request) is False

    def test_inactive_user_denied(
        self, empresa_autoprime, request_factory
    ):
        """Usuário inativo não tem permissão."""
        user = UserFactory(email="inativo@autoprime.com", is_active=False)
        FuncionarioFactory(usuario=user, empresa=empresa_autoprime)

        request = request_factory.get("/gerentes/")
        request.user = user

        assert gerente_site.has_permission(request) is False


@pytest.mark.django_db
class TestCrossTenantAccessDenied:
    """
    Testes que verificam que funcionário de uma empresa
    NÃO pode acessar dados de outra empresa.

    O TenantMiddleware valida que user.empresa == request.tenant
    e retorna 403 Forbidden se não corresponder.
    """

    def test_funcionario_autoprime_denied_autolitros_admin_via_subdomain(
        self, client, funcionario_autoprime, empresa_autolitros
    ):
        """
        Funcionário da AutoPrime não pode acessar admin da AutoLitros
        via subdomínio autolitros.localhost.
        """
        client.force_login(funcionario_autoprime.usuario)

        response = client.get(
            "/gerentes/",
            HTTP_HOST="autolitros.localhost:8000",
        )

        # Deve ser negado (403 Forbidden)
        assert response.status_code == 403

    def test_funcionario_autoprime_sees_only_own_data_in_gerente_admin(
        self,
        request_factory,
        funcionario_autoprime,
        inventario_autoprime,
        inventario_autolitros,
    ):
        """
        Funcionário da AutoPrime só vê inventários da AutoPrime
        no admin de gerentes.
        """
        from plataforma_de_servicos.inventario.admin.gerente_admin import (
            InventarioGerenteAdmin,
        )

        model_admin = InventarioGerenteAdmin(Inventario, gerente_site)
        request = request_factory.get("/gerentes/inventario/inventario/")
        request.user = funcionario_autoprime.usuario
        request.tenant = funcionario_autoprime.empresa

        qs = model_admin.get_queryset(request)

        assert qs.count() == 1
        assert inventario_autoprime in qs
        assert inventario_autolitros not in qs

    def test_funcionario_autolitros_sees_only_own_data_in_gerente_admin(
        self,
        request_factory,
        funcionario_autolitros,
        inventario_autoprime,
        inventario_autolitros,
    ):
        """
        Funcionário da AutoLitros só vê inventários da AutoLitros
        no admin de gerentes.
        """
        from plataforma_de_servicos.inventario.admin.gerente_admin import (
            InventarioGerenteAdmin,
        )

        model_admin = InventarioGerenteAdmin(Inventario, gerente_site)
        request = request_factory.get("/gerentes/inventario/inventario/")
        request.user = funcionario_autolitros.usuario
        request.tenant = funcionario_autolitros.empresa

        qs = model_admin.get_queryset(request)

        assert qs.count() == 1
        assert inventario_autolitros in qs
        assert inventario_autoprime not in qs

    def test_funcionario_cannot_see_other_empresa_produtos(
        self,
        request_factory,
        funcionario_autoprime,
        produto_autoprime,
        produto_autolitros,
    ):
        """
        Funcionário da AutoPrime não pode ver produtos da AutoLitros.
        """
        from plataforma_de_servicos.produto.admin.gerente_admin import (
            ProdutoGerenteAdmin,
        )

        model_admin = ProdutoGerenteAdmin(Produto, gerente_site)
        request = request_factory.get("/gerentes/produto/produto/")
        request.user = funcionario_autoprime.usuario
        request.tenant = funcionario_autoprime.empresa

        qs = model_admin.get_queryset(request)

        assert qs.count() == 1
        assert produto_autoprime in qs
        assert produto_autolitros not in qs


@pytest.mark.django_db
class TestDataIsolationInForms:
    """Testes de isolamento de dados em formulários do admin."""

    def test_create_produto_auto_fills_empresa(
        self,
        request_factory,
        funcionario_autoprime,
        categoria_autoprime,
    ):
        """
        Ao criar produto no admin de gerentes,
        empresa é auto-preenchida com o tenant.
        """
        from plataforma_de_servicos.produto.admin.gerente_admin import (
            ProdutoGerenteAdmin,
        )

        model_admin = ProdutoGerenteAdmin(Produto, gerente_site)
        request = request_factory.post("/gerentes/produto/produto/add/")
        request.user = funcionario_autoprime.usuario
        request.tenant = funcionario_autoprime.empresa

        novo_produto = Produto(
            produto="Novo Produto",
            preco=100.00,
            categoria=categoria_autoprime,
        )

        model_admin.save_model(request, novo_produto, None, change=False)

        assert novo_produto.empresa == funcionario_autoprime.empresa

    def test_cannot_edit_other_empresa_produto(
        self,
        request_factory,
        funcionario_autoprime,
        produto_autolitros,
    ):
        """
        Funcionário da AutoPrime não pode editar produto da AutoLitros.

        Mesmo que consiga submeter o form, o queryset filtrado
        não deve incluir o produto de outra empresa.
        """
        from plataforma_de_servicos.produto.admin.gerente_admin import (
            ProdutoGerenteAdmin,
        )

        model_admin = ProdutoGerenteAdmin(Produto, gerente_site)
        request = request_factory.get(
            f"/gerentes/produto/produto/{produto_autolitros.pk}/change/"
        )
        request.user = funcionario_autoprime.usuario
        request.tenant = funcionario_autoprime.empresa

        qs = model_admin.get_queryset(request)

        # Produto da AutoLitros não aparece no queryset
        assert produto_autolitros not in qs


@pytest.mark.django_db
class TestSuperuserAccess:
    """Testes de acesso de superusuário."""

    def test_superuser_sees_all_data_without_tenant(
        self,
        request_factory,
        superuser,
        inventario_autoprime,
        inventario_autolitros,
    ):
        """
        Superusuário sem tenant definido vê todos os dados.
        """
        from plataforma_de_servicos.inventario.admin.gerente_admin import (
            InventarioGerenteAdmin,
        )
        from django.contrib import admin as main_admin

        # No admin principal, sem tenant
        model_admin = InventarioGerenteAdmin(Inventario, main_admin.site)
        request = request_factory.get("/admin/inventario/inventario/")
        request.user = superuser
        request.tenant = None

        qs = model_admin.get_queryset(request)

        assert qs.count() == 2
        assert inventario_autoprime in qs
        assert inventario_autolitros in qs

    def test_superuser_can_filter_by_tenant_via_query_param(
        self,
        client,
        superuser,
        empresa_autoprime,
    ):
        """
        Superusuário pode filtrar por tenant usando ?tenant=slug.
        """
        client.force_login(superuser)

        response = client.get(
            "/gerentes/?tenant=autoprime",
            HTTP_HOST="localhost:8000",
        )

        # Deve ter acesso e o tenant deve estar no contexto
        assert response.status_code == 200

    def test_superuser_can_access_any_empresa_subdomain(
        self,
        client,
        superuser,
        empresa_autoprime,
        empresa_autolitros,
    ):
        """
        Superusuário pode acessar qualquer subdomínio de empresa.
        """
        client.force_login(superuser)

        # Acessa AutoPrime
        response_autoprime = client.get(
            "/gerentes/",
            HTTP_HOST="autoprime.localhost:8000",
        )
        assert response_autoprime.status_code == 200

        # Acessa AutoLitros
        response_autolitros = client.get(
            "/gerentes/",
            HTTP_HOST="autolitros.localhost:8000",
        )
        assert response_autolitros.status_code == 200


@pytest.mark.django_db
class TestTenantContextInAdmin:
    """Testes do contexto de tenant no admin."""

    def test_tenant_info_in_admin_context(
        self,
        request_factory,
        funcionario_autoprime,
    ):
        """
        Contexto do admin inclui informações do tenant.
        """
        request = request_factory.get("/gerentes/")
        request.user = funcionario_autoprime.usuario
        request.tenant = funcionario_autoprime.empresa
        request.session = {}

        context = gerente_site.each_context(request)

        assert context["tenant"] == funcionario_autoprime.empresa
        assert context["tenant_name"] == funcionario_autoprime.empresa.nome

    def test_tenant_customization_applied(
        self,
        request_factory,
        empresa_autoprime,
        funcionario_autoprime,
    ):
        """
        Customizações do tenant são aplicadas no contexto.
        """
        # Configura customizações
        empresa_autoprime.admin_title = "Portal AutoPrime"
        empresa_autoprime.admin_subtitle = "Gestão de Peças"
        empresa_autoprime.primary_color = "#ff0000"
        empresa_autoprime.save()

        request = request_factory.get("/gerentes/")
        request.user = funcionario_autoprime.usuario
        request.tenant = empresa_autoprime
        request.session = {}

        context = gerente_site.each_context(request)

        assert context["tenant_customization"]["site_header"] == "Portal AutoPrime"
        assert context["theme_colors"]["primary"] == "#ff0000"
