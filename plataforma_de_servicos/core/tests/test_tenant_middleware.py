"""
Testes para o TenantMiddleware.

Verifica o isolamento de tenant por subdomínio e validação de acesso.
"""
import pytest
from django.http import Http404
from django.test import RequestFactory

from plataforma_de_servicos.core.middleware.tenant import TenantMiddleware
from plataforma_de_servicos.empresa.models import Empresa
from plataforma_de_servicos.empresa.tests.factories.empresa_factory import EmpresaFactory
from plataforma_de_servicos.users.models import Funcionario, User
from plataforma_de_servicos.users.tests.factories import FuncionarioFactory, UserFactory


@pytest.fixture
def middleware():
    """Instância do middleware com uma response dummy."""
    def get_response(request):
        return request  # Retorna o request para inspeção
    return TenantMiddleware(get_response)


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
    user = UserFactory(email="vendedor@autoprime.com")
    return FuncionarioFactory(usuario=user, empresa=empresa_autoprime)


@pytest.fixture
def funcionario_autolitros(empresa_autolitros):
    """Funcionário da empresa AutoLitros."""
    user = UserFactory(email="vendedor@autolitros.com")
    return FuncionarioFactory(usuario=user, empresa=empresa_autolitros)


@pytest.fixture
def superuser(db):
    """Superusuário para testes."""
    return User.objects.create_superuser(
        email="super@admin.com",
        password="password123",
    )


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.mark.django_db
class TestSubdomainResolution:
    """Testes de resolução de tenant por subdomínio."""

    def test_subdomain_resolves_correct_tenant(
        self, middleware, request_factory, empresa_autoprime
    ):
        """Subdomínio válido resolve para o tenant correto."""
        request = request_factory.get("/")
        request.META["HTTP_HOST"] = "autoprime.localhost:8000"
        request.session = {}

        result = middleware(request)

        assert result.tenant == empresa_autoprime
        assert result.is_main_domain is False

    def test_lvh_me_subdomain_resolves_tenant(
        self, middleware, request_factory, empresa_autoprime
    ):
        """Subdomínio lvh.me resolve corretamente."""
        request = request_factory.get("/")
        request.META["HTTP_HOST"] = "autoprime.lvh.me:8000"
        request.session = {}

        result = middleware(request)

        assert result.tenant == empresa_autoprime
        assert result.is_main_domain is False

    def test_invalid_subdomain_returns_no_tenant(
        self, middleware, request_factory
    ):
        """Subdomínio inválido não resolve tenant (retorna None)."""
        request = request_factory.get("/")
        request.META["HTTP_HOST"] = "empresainexistente.localhost:8000"
        request.session = {}

        result = middleware(request)

        assert result.tenant is None
        assert result.is_main_domain is False

    def test_main_domain_has_no_tenant(
        self, middleware, request_factory, empresa_autoprime
    ):
        """Domínio principal não tem tenant automaticamente."""
        request = request_factory.get("/")
        request.META["HTTP_HOST"] = "localhost:8000"
        request.session = {}

        result = middleware(request)

        assert result.tenant is None
        assert result.is_main_domain is True

    def test_www_is_treated_as_main_domain(
        self, middleware, request_factory, empresa_autoprime
    ):
        """www.domain.com é tratado como domínio principal."""
        request = request_factory.get("/")
        request.META["HTTP_HOST"] = "www.example.com"
        request.session = {}

        result = middleware(request)

        assert result.is_main_domain is True


@pytest.mark.django_db
class TestAdminAccessBlocking:
    """Testes de bloqueio do /admin/ em subdomínios."""

    def test_admin_blocked_on_subdomain(
        self, middleware, request_factory, empresa_autoprime
    ):
        """/admin/ é bloqueado em subdomínio (retorna 404)."""
        request = request_factory.get("/admin/")
        request.META["HTTP_HOST"] = "autoprime.localhost:8000"
        request.session = {}

        with pytest.raises(Http404):
            middleware(request)

    def test_admin_accessible_on_main_domain(
        self, middleware, request_factory
    ):
        """/admin/ é acessível no domínio principal."""
        request = request_factory.get("/admin/")
        request.META["HTTP_HOST"] = "localhost:8000"
        request.session = {}

        result = middleware(request)

        # Não levanta exceção, permite acesso
        assert result.tenant is None
        assert result.is_main_domain is True


@pytest.mark.django_db
class TestGerentesAdminTenantResolution:
    """Testes de resolução de tenant para /gerentes/."""

    def test_gerentes_on_subdomain_denies_cross_tenant_access(
        self, middleware, request_factory, empresa_autoprime, funcionario_autolitros
    ):
        """
        Funcionário de uma empresa não pode acessar /gerentes/
        de outra empresa via subdomínio - retorna 403 Forbidden.
        """
        from django.http import HttpResponseForbidden

        request = request_factory.get("/gerentes/")
        request.META["HTTP_HOST"] = "autoprime.localhost:8000"
        request.user = funcionario_autolitros.usuario
        request.session = {}

        result = middleware(request)

        # Deve retornar 403 Forbidden
        assert isinstance(result, HttpResponseForbidden)
        assert result.status_code == 403

    def test_gerentes_on_subdomain_allows_own_empresa_access(
        self, middleware, request_factory, empresa_autoprime, funcionario_autoprime
    ):
        """
        Funcionário pode acessar /gerentes/ da sua própria empresa via subdomínio.
        """
        request = request_factory.get("/gerentes/")
        request.META["HTTP_HOST"] = "autoprime.localhost:8000"
        request.user = funcionario_autoprime.usuario
        request.session = {}

        result = middleware(request)

        # Deve passar e ter tenant definido
        assert result.tenant == empresa_autoprime

    def test_gerentes_on_main_domain_uses_user_tenant(
        self, middleware, request_factory, funcionario_autoprime
    ):
        """/gerentes/ no domínio principal usa tenant do usuário."""
        request = request_factory.get("/gerentes/")
        request.META["HTTP_HOST"] = "localhost:8000"
        request.user = funcionario_autoprime.usuario
        request.session = {}

        result = middleware(request)

        assert result.tenant == funcionario_autoprime.empresa

    def test_gerentes_superuser_can_select_tenant_via_query(
        self, middleware, request_factory, superuser, empresa_autoprime
    ):
        """Superusuário pode selecionar tenant via query param."""
        request = request_factory.get("/gerentes/", {"tenant": "autoprime"})
        request.META["HTTP_HOST"] = "localhost:8000"
        request.user = superuser
        request.session = {}

        result = middleware(request)

        assert result.tenant == empresa_autoprime


@pytest.mark.django_db
class TestStaticRequests:
    """Testes para requisições de arquivos estáticos."""

    def test_static_requests_bypass_tenant_resolution(
        self, middleware, request_factory
    ):
        """Requisições de arquivos estáticos não processam tenant."""
        request = request_factory.get("/static/css/main.css")
        request.META["HTTP_HOST"] = "autoprime.localhost:8000"
        # Não precisa de session para requests estáticos

        result = middleware(request)

        # Tenant não é resolvido para estáticos
        assert result.tenant is None

    def test_media_requests_bypass_tenant_resolution(
        self, middleware, request_factory
    ):
        """Requisições de mídia não processam tenant."""
        request = request_factory.get("/media/images/logo.png")
        request.META["HTTP_HOST"] = "autoprime.localhost:8000"

        result = middleware(request)

        assert result.tenant is None


@pytest.mark.django_db
class TestDevTenantSupport:
    """Testes para suporte a tenant em desenvolvimento."""

    def test_dev_tenant_from_query_param(
        self, middleware, request_factory, empresa_autoprime
    ):
        """Pode definir tenant via query param no domínio principal."""
        request = request_factory.get("/", {"tenant": "autoprime"})
        request.META["HTTP_HOST"] = "localhost:8000"
        request.session = {}

        result = middleware(request)

        assert result.tenant == empresa_autoprime

    def test_dev_tenant_persists_in_session(
        self, middleware, request_factory, empresa_autoprime
    ):
        """Tenant de desenvolvimento é persistido na sessão."""
        session = {}

        # Primeira requisição com query param
        request1 = request_factory.get("/", {"tenant": "autoprime"})
        request1.META["HTTP_HOST"] = "localhost:8000"
        request1.session = session

        middleware(request1)

        # Segunda requisição sem query param deve usar sessão
        request2 = request_factory.get("/")
        request2.META["HTTP_HOST"] = "localhost:8000"
        request2.session = session

        result = middleware(request2)

        assert result.tenant == empresa_autoprime


@pytest.mark.django_db
class TestIsMainDomainMethod:
    """Testes para o método _is_main_domain."""

    def test_localhost_is_main_domain(self, middleware, request_factory):
        """localhost é domínio principal."""
        request = request_factory.get("/")
        request.META["HTTP_HOST"] = "localhost:8000"
        request.session = {}

        middleware(request)

        assert request.is_main_domain is True

    def test_127_0_0_1_is_main_domain(self, middleware, request_factory):
        """127.0.0.1 é domínio principal."""
        request = request_factory.get("/")
        request.META["HTTP_HOST"] = "127.0.0.1:8000"
        request.session = {}

        middleware(request)

        assert request.is_main_domain is True

    def test_subdomain_localhost_is_not_main_domain(
        self, middleware, request_factory, empresa_autoprime
    ):
        """empresa.localhost NÃO é domínio principal."""
        request = request_factory.get("/")
        request.META["HTTP_HOST"] = "autoprime.localhost:8000"
        request.session = {}

        middleware(request)

        assert request.is_main_domain is False

    def test_simple_domain_is_main_domain(self, middleware, request_factory):
        """example.com (2 partes) é domínio principal."""
        request = request_factory.get("/")
        request.META["HTTP_HOST"] = "example.com"
        request.session = {}

        middleware(request)

        assert request.is_main_domain is True

    def test_three_part_domain_is_subdomain(
        self, middleware, request_factory, empresa_autoprime
    ):
        """empresa.example.com (3 partes) é subdomínio."""
        # Cria empresa com slug "empresa" para o teste
        EmpresaFactory(nome="Empresa", slug="empresa")

        request = request_factory.get("/")
        request.META["HTTP_HOST"] = "empresa.example.com"
        request.session = {}

        middleware(request)

        assert request.is_main_domain is False
