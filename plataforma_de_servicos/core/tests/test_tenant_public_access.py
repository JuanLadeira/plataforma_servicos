"""
Testes de acesso público com isolamento de tenant.

Verifica que o catálogo público mostra apenas dados
da empresa correta baseado no subdomínio.
"""
import pytest
from django.test import Client, RequestFactory

from plataforma_de_servicos.empresa.tests.factories.empresa_factory import EmpresaFactory
from plataforma_de_servicos.inventario.models import Inventario, InventarioSaldo
from plataforma_de_servicos.produto.models import Produto, Categoria, VariacaoProduto
from plataforma_de_servicos.produto.models.atributos import Atributo, ValorAtributo
from plataforma_de_servicos.users.models import User
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
    user = UserFactory(email="user@autoprime.com")
    return FuncionarioFactory(usuario=user, empresa=empresa_autoprime)


@pytest.fixture
def funcionario_autolitros(empresa_autolitros):
    """Funcionário da empresa AutoLitros."""
    user = UserFactory(email="user@autolitros.com")
    return FuncionarioFactory(usuario=user, empresa=empresa_autolitros)


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
def inventario_autoprime(empresa_autoprime):
    """Inventário da AutoPrime com exibição na vitrine."""
    return Inventario.objects.create(
        nome="Vitrine AutoPrime",
        empresa=empresa_autoprime,
        is_ativo=True,
        exibir_na_vitrine=True,
    )


@pytest.fixture
def inventario_autolitros(empresa_autolitros):
    """Inventário da AutoLitros com exibição na vitrine."""
    return Inventario.objects.create(
        nome="Vitrine AutoLitros",
        empresa=empresa_autolitros,
        is_ativo=True,
        exibir_na_vitrine=True,
    )


@pytest.fixture
def produto_autoprime(categoria_autoprime, empresa_autoprime, inventario_autoprime):
    """Produto da empresa AutoPrime com variação e estoque para vitrine."""
    produto = Produto.objects.create(
        produto="Filtro de Ar Premium",
        preco=50.00,
        categoria=categoria_autoprime,
        empresa=empresa_autoprime,
        disponivel=True,
    )

    # Cria atributo vinculado à categoria (empresa herdada via categoria)
    atributo = Atributo.objects.create(nome="Tamanho", categoria=categoria_autoprime)
    valor = ValorAtributo.objects.create(atributo=atributo, valor="Médio")

    variacao = VariacaoProduto.objects.create(
        produto=produto,
        preco=55.00,
        estoque=10,
    )
    variacao.valores.add(valor)
    variacao.gerar_sku()
    variacao.save()

    # Cria saldo no inventário para exibir na vitrine
    InventarioSaldo.objects.create(
        inventario=inventario_autoprime,
        produto=produto,
        quantidade=10,
    )

    return produto


@pytest.fixture
def produto_autolitros(categoria_autolitros, empresa_autolitros, inventario_autolitros):
    """Produto da empresa AutoLitros com variação e estoque para vitrine."""
    produto = Produto.objects.create(
        produto="Óleo 5W30 Sintético",
        preco=80.00,
        categoria=categoria_autolitros,
        empresa=empresa_autolitros,
        disponivel=True,
    )

    # Cria atributo vinculado à categoria (empresa herdada via categoria)
    atributo = Atributo.objects.create(nome="Volume", categoria=categoria_autolitros)
    valor = ValorAtributo.objects.create(atributo=atributo, valor="1 Litro")

    variacao = VariacaoProduto.objects.create(
        produto=produto,
        preco=85.00,
        estoque=50,
    )
    variacao.valores.add(valor)
    variacao.gerar_sku()
    variacao.save()

    # Cria saldo no inventário para exibir na vitrine
    InventarioSaldo.objects.create(
        inventario=inventario_autolitros,
        produto=produto,
        quantidade=50,
    )

    return produto


@pytest.fixture
def client():
    return Client()


@pytest.mark.django_db
class TestPublicCatalogIsolation:
    """Testes de isolamento do catálogo público."""

    def test_anonymous_sees_autoprime_products_on_autoprime_subdomain(
        self, client, empresa_autoprime, produto_autoprime, produto_autolitros
    ):
        """
        Usuário anônimo no subdomínio autoprime.localhost
        só vê produtos da AutoPrime.
        """
        response = client.get("/", HTTP_HOST="autoprime.localhost:8000")

        assert response.status_code == 200
        content = response.content.decode()

        # Deve conter produto da AutoPrime
        assert "Filtro de Ar Premium" in content

        # NÃO deve conter produto da AutoLitros
        assert "Óleo 5W30 Sintético" not in content

    def test_anonymous_sees_autolitros_products_on_autolitros_subdomain(
        self, client, empresa_autolitros, produto_autoprime, produto_autolitros
    ):
        """
        Usuário anônimo no subdomínio autolitros.localhost
        só vê produtos da AutoLitros.
        """
        response = client.get("/", HTTP_HOST="autolitros.localhost:8000")

        assert response.status_code == 200
        content = response.content.decode()

        # Deve conter produto da AutoLitros
        assert "Óleo 5W30 Sintético" in content

        # NÃO deve conter produto da AutoPrime
        assert "Filtro de Ar Premium" not in content

    def test_anonymous_sees_autoprime_categories_on_autoprime_subdomain(
        self, client, empresa_autoprime, categoria_autoprime, categoria_autolitros
    ):
        """
        Usuário anônimo só vê categorias da empresa do subdomínio.
        """
        response = client.get("/", HTTP_HOST="autoprime.localhost:8000")

        assert response.status_code == 200
        content = response.content.decode()

        assert "Peças AutoPrime" in content
        assert "Óleos AutoLitros" not in content


@pytest.mark.django_db
class TestProductDetailIsolation:
    """Testes de isolamento na página de detalhe do produto."""

    def test_cannot_access_other_empresa_product_detail(
        self, client, empresa_autoprime, produto_autolitros
    ):
        """
        Não pode acessar detalhe de produto de outra empresa
        via subdomínio incorreto.
        """
        response = client.get(
            f"/produto/{produto_autolitros.slug}/",
            HTTP_HOST="autoprime.localhost:8000",
        )

        # Deve retornar 404 porque produto não pertence à AutoPrime
        assert response.status_code == 404

    def test_can_access_own_empresa_product_detail(
        self, client, empresa_autoprime, produto_autoprime
    ):
        """
        Pode acessar detalhe de produto da própria empresa.
        """
        response = client.get(
            f"/produto/{produto_autoprime.slug}/",
            HTTP_HOST="autoprime.localhost:8000",
        )

        assert response.status_code == 200
        assert "Filtro de Ar Premium" in response.content.decode()


@pytest.mark.django_db
class TestVariacaoDetailIsolation:
    """Testes de isolamento na página de detalhe da variação."""

    def test_cannot_access_other_empresa_variacao_detail(
        self, client, empresa_autoprime, produto_autolitros
    ):
        """
        Não pode acessar detalhe de variação de outra empresa
        via subdomínio incorreto.
        """
        variacao = produto_autolitros.variacoes.first()

        response = client.get(
            f"/variacao/{variacao.sku}/",
            HTTP_HOST="autoprime.localhost:8000",
        )

        # Deve retornar 404
        assert response.status_code == 404

    def test_can_access_own_empresa_variacao_detail(
        self, client, empresa_autoprime, produto_autoprime
    ):
        """
        Pode acessar detalhe de variação da própria empresa.
        """
        variacao = produto_autoprime.variacoes.first()

        response = client.get(
            f"/variacao/{variacao.sku}/",
            HTTP_HOST="autoprime.localhost:8000",
        )

        assert response.status_code == 200


@pytest.mark.django_db
class TestCategorySearchIsolation:
    """Testes de isolamento na busca de categorias."""

    def test_category_search_returns_only_own_empresa_categories(
        self, client, empresa_autoprime, categoria_autoprime, categoria_autolitros
    ):
        """
        Busca de categorias retorna apenas categorias da empresa atual.
        """
        response = client.post(
            "/search/category/",
            {"search": "Peças"},
            HTTP_HOST="autoprime.localhost:8000",
        )

        assert response.status_code == 200
        content = response.content.decode()

        assert "Peças AutoPrime" in content
        # Mesmo buscando termo genérico, não deve mostrar outras empresas
        assert "Óleos AutoLitros" not in content


@pytest.mark.django_db
class TestLoggedUserPublicAccess:
    """
    Testes de acesso público para usuários logados.

    O TenantMiddleware valida que user.empresa == request.tenant
    e retorna 403 Forbidden se não corresponder.
    """

    def test_logged_user_sees_own_empresa_products(
        self, client, funcionario_autoprime, produto_autoprime, produto_autolitros
    ):
        """
        Usuário logado vê apenas produtos da empresa do subdomínio.
        """
        client.force_login(funcionario_autoprime.usuario)

        response = client.get("/", HTTP_HOST="autoprime.localhost:8000")

        assert response.status_code == 200
        content = response.content.decode()

        assert "Filtro de Ar Premium" in content
        assert "Óleo 5W30 Sintético" not in content

    def test_logged_user_denied_access_to_other_empresa_home(
        self, client, funcionario_autoprime, empresa_autolitros
    ):
        """
        Funcionário da AutoPrime não pode acessar home da AutoLitros.
        """
        client.force_login(funcionario_autoprime.usuario)

        response = client.get("/", HTTP_HOST="autolitros.localhost:8000")

        # Deve ser negado (403 Forbidden)
        assert response.status_code == 403


@pytest.mark.django_db
class TestMainDomainAccess:
    """Testes de acesso no domínio principal (sem subdomínio)."""

    def test_main_domain_without_tenant_shows_no_products(
        self, client, produto_autoprime, produto_autolitros
    ):
        """
        Domínio principal sem tenant não mostra produtos
        (ou mostra página de seleção de empresa).
        """
        response = client.get("/", HTTP_HOST="localhost:8000")

        assert response.status_code == 200
        content = response.content.decode()

        # Sem tenant, não deve mostrar produtos de nenhuma empresa
        assert "Filtro de Ar Premium" not in content
        assert "Óleo 5W30 Sintético" not in content

    def test_main_domain_with_tenant_param_shows_products(
        self, client, empresa_autoprime, produto_autoprime, produto_autolitros
    ):
        """
        Domínio principal com ?tenant=slug mostra produtos da empresa.
        """
        response = client.get(
            "/?tenant=autoprime",
            HTTP_HOST="localhost:8000",
        )

        assert response.status_code == 200
        content = response.content.decode()

        assert "Filtro de Ar Premium" in content
        assert "Óleo 5W30 Sintético" not in content


@pytest.mark.django_db
class TestHTMXPartialIsolation:
    """Testes de isolamento em requisições HTMX parciais."""

    def test_htmx_product_list_isolated_by_tenant(
        self, client, empresa_autoprime, produto_autoprime, produto_autolitros
    ):
        """
        Requisição HTMX de lista de produtos respeita isolamento de tenant.
        """
        response = client.get(
            "/",
            HTTP_HOST="autoprime.localhost:8000",
            HTTP_HX_REQUEST="true",
        )

        assert response.status_code == 200
        content = response.content.decode()

        assert "Filtro de Ar Premium" in content
        assert "Óleo 5W30 Sintético" not in content


@pytest.mark.django_db
class TestInvalidSubdomain:
    """Testes para subdomínios inválidos."""

    def test_invalid_subdomain_shows_empty_catalog(
        self, client, produto_autoprime, produto_autolitros
    ):
        """
        Subdomínio inválido (empresa não existe) mostra catálogo vazio.
        """
        response = client.get("/", HTTP_HOST="empresainexistente.localhost:8000")

        assert response.status_code == 200
        content = response.content.decode()

        # Sem tenant válido, não deve mostrar produtos
        assert "Filtro de Ar Premium" not in content
        assert "Óleo 5W30 Sintético" not in content
