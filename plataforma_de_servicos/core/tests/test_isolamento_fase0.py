"""
Testes de regressão de isolamento entre empresas (Fase 0 de segurança).

Cada teste cria dados em duas empresas e garante que a empresa A
nunca enxerga nem altera dados da empresa B.
"""
from decimal import Decimal

import pytest
from django.test import Client

from plataforma_de_servicos.corretor.models import InteresseCompra
from plataforma_de_servicos.corretor.models import StatusInteresse
from plataforma_de_servicos.corretor.tests.factories import InteresseCompraFactory
from plataforma_de_servicos.corretor.tests.factories import ItemInteresseFactory
from plataforma_de_servicos.empresa.tests.factories import EmpresaFactory
from plataforma_de_servicos.produto.models import Categoria
from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.users.models import PapelFuncionario
from plataforma_de_servicos.users.tests.factories import FuncionarioFactory
from plataforma_de_servicos.users.tests.factories import UserFactory

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def empresa_a():
    return EmpresaFactory(nome="Empresa A", slug="empresaa")


@pytest.fixture
def empresa_b():
    return EmpresaFactory(nome="Empresa B", slug="empresab")


def _funcionario(empresa, papel):
    user = UserFactory()
    return FuncionarioFactory(usuario=user, empresa=empresa, papel=papel)


@pytest.fixture
def gerente_a(empresa_a):
    return _funcionario(empresa_a, PapelFuncionario.GERENTE)


@pytest.fixture
def vendedor_a(empresa_a):
    return _funcionario(empresa_a, PapelFuncionario.VENDEDOR)


@pytest.fixture
def lead_b(empresa_b):
    return InteresseCompraFactory(
        empresa=empresa_b,
        nome_cliente="Cliente da B",
        email_cliente="cliente@empresab.com",
        status=StatusInteresse.NOVO,
    )


def _logado(funcionario):
    client = Client()
    client.force_login(funcionario.usuario)
    return client


class TestPortalVendedorDominioPrincipal:
    """/vendedores/ no domínio principal usa a empresa do funcionário."""

    URL = "/vendedores/corretor/interessecompra/"

    @pytest.mark.parametrize("papel", [PapelFuncionario.GERENTE, PapelFuncionario.VENDEDOR])
    def test_listagem_nao_mostra_leads_de_outra_empresa(
        self, empresa_a, empresa_b, lead_b, papel,
    ):
        lead_a = InteresseCompraFactory(empresa=empresa_a, nome_cliente="Cliente da A")
        client = _logado(_funcionario(empresa_a, papel))

        response = client.get(self.URL, HTTP_HOST="localhost")

        assert response.status_code == 200
        content = response.content.decode()
        assert lead_a.nome_cliente in content
        assert lead_b.nome_cliente not in content

    def test_detalhe_de_lead_de_outra_empresa_nao_abre(self, gerente_a, lead_b):
        client = _logado(gerente_a)

        response = client.get(f"{self.URL}{lead_b.pk}/change/", HTTP_HOST="localhost")

        content = response.content.decode()
        assert lead_b.nome_cliente not in content
        assert lead_b.email_cliente not in content
        assert response.status_code in (302, 404)

    def test_acao_atender_em_lead_de_outra_empresa(self, vendedor_a, lead_b):
        client = _logado(vendedor_a)

        response = client.get(
            f"{self.URL}{lead_b.pk}/atender/", HTTP_HOST="localhost",
        )

        lead_b.refresh_from_db()
        assert lead_b.status == StatusInteresse.NOVO
        assert lead_b.corretor is None
        assert response.status_code in (302, 403, 404)


class TestMixinFailClosed:
    """Sem tenant, usuário que não é superusuário não vê nada."""

    def test_funcionario_sem_empresa_nao_ve_leads(self, empresa_b, lead_b):
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory

        from plataforma_de_servicos.core.admin.sites.vendedor_admin_site import (
            InteresseCompraVendedorAdmin,
        )

        admin = InteresseCompraVendedorAdmin(InteresseCompra, AdminSite(name="vendedores"))
        request = RequestFactory().get("/vendedores/")
        request.user = _funcionario(None, PapelFuncionario.GERENTE).usuario
        request.tenant = None

        assert admin.get_queryset(request).count() == 0


class TestGerenteProdutoAtributosApi:
    """API de atributos do site de gerentes não lê produto de outra empresa."""

    def test_produto_de_outra_empresa_retorna_404(self, gerente_a, empresa_b):
        categoria_b = Categoria.objects.create(categoria="Cat B", empresa=empresa_b)
        produto_b = Produto.objects.create(
            produto="Produto B", preco=10, categoria=categoria_b, empresa=empresa_b,
        )
        client = _logado(gerente_a)

        response = client.get(
            f"/gerentes/api/produto/{produto_b.pk}/atributos/", HTTP_HOST="localhost",
        )

        assert response.status_code == 404


class TestVitrineSemTenant:
    """Rotas públicas de produto no domínio principal não expõem dados."""

    def test_produto_detail_sem_tenant_retorna_404(self, empresa_b):
        produto_b = Produto.objects.create(produto="Produto B", preco=10, empresa=empresa_b)

        response = Client().get(f"/produto/{produto_b.slug}/", HTTP_HOST="localhost")

        assert response.status_code == 404

    def test_produto_detail_de_outra_empresa_retorna_404(self, empresa_a, empresa_b):
        produto_b = Produto.objects.create(produto="Produto B", preco=10, empresa=empresa_b)

        response = Client().get(
            f"/produto/{produto_b.slug}/", HTTP_HOST=f"{empresa_a.slug}.localhost",
        )

        assert response.status_code == 404


class TestConversaoLeadOrdemPorEmpresa:
    """A ordem só vincula produtos da empresa do lead."""

    def test_nao_vincula_produto_de_mesmo_nome_de_outra_empresa(self, empresa_a, empresa_b):
        Produto.objects.create(produto="Kit Velas", preco=10, empresa=empresa_b)
        produto_a = Produto.objects.create(produto="Kit Velas", preco=10, empresa=empresa_a)
        interesse = InteresseCompraFactory(empresa=empresa_a, status=StatusInteresse.NOVO)
        ItemInteresseFactory(
            interesse=interesse,
            produto_nome="Kit Velas",
            quantidade=1,
            preco_unitario=Decimal("10.00"),
        )

        interesse.status = StatusInteresse.CONVERTIDO
        interesse.save()

        item = interesse.ordem_compra.itens.get()
        assert item.produto == produto_a

    def test_produto_so_existente_em_outra_empresa_fica_sem_vinculo(
        self, empresa_a, empresa_b,
    ):
        Produto.objects.create(produto="Exclusivo B", preco=10, empresa=empresa_b)
        interesse = InteresseCompraFactory(empresa=empresa_a, status=StatusInteresse.NOVO)
        ItemInteresseFactory(
            interesse=interesse,
            produto_nome="Exclusivo B",
            quantidade=1,
            preco_unitario=Decimal("10.00"),
        )

        interesse.status = StatusInteresse.CONVERTIDO
        interesse.save()

        assert interesse.ordem_compra.itens.get().produto is None
