from decimal import Decimal

import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from plataforma_de_servicos.core.admin.sites.gerente_admin_site import gerente_site
from plataforma_de_servicos.users.tests.factories import UserFactory
from plataforma_de_servicos.vendas.admin import OrdemCompraGerenteAdmin
from plataforma_de_servicos.vendas.admin.forms import CancelamentoOrdemForm
from plataforma_de_servicos.vendas.admin.forms import RejeicaoOrdemForm
from plataforma_de_servicos.vendas.admin.ordem_compra_admin import ItemOrdemCompraGerenteInline
from plataforma_de_servicos.vendas.admin.ordem_compra_admin import ItemOrdemCompraInline
from plataforma_de_servicos.vendas.admin.ordem_compra_admin import OrdemCompraAdmin
from plataforma_de_servicos.vendas.models import OrdemCompra
from plataforma_de_servicos.vendas.models import StatusOrdemCompra
from plataforma_de_servicos.vendas.tests.factories import ItemOrdemCompraFactory
from plataforma_de_servicos.vendas.tests.factories import OrdemCompraFactory


@pytest.fixture
def admin_site():
    return AdminSite()


@pytest.fixture
def gerente_admin():
    return OrdemCompraGerenteAdmin(OrdemCompra, gerente_site)


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def admin_user(db):
    return UserFactory(is_staff=True, is_superuser=True)


@pytest.mark.django_db
class TestRejeicaoOrdemForm:
    def test_form_valido_com_motivo(self):
        form = RejeicaoOrdemForm(data={"motivo": "Motivo de teste"})
        assert form.is_valid()

    def test_form_invalido_sem_motivo(self):
        form = RejeicaoOrdemForm(data={"motivo": ""})
        assert not form.is_valid()
        assert "motivo" in form.errors

    def test_form_invalido_motivo_none(self):
        form = RejeicaoOrdemForm(data={})
        assert not form.is_valid()


@pytest.mark.django_db
class TestCancelamentoOrdemForm:
    def test_form_valido_com_motivo(self):
        form = CancelamentoOrdemForm(data={"motivo": "Motivo de teste"})
        assert form.is_valid()

    def test_form_valido_sem_motivo(self):
        """Motivo e opcional no cancelamento."""
        form = CancelamentoOrdemForm(data={"motivo": ""})
        assert form.is_valid()

    def test_form_valido_motivo_none(self):
        form = CancelamentoOrdemForm(data={})
        assert form.is_valid()


@pytest.mark.django_db
class TestOrdemCompraGerenteAdminPermissions:
    """Testes para metodos de permissao condicional."""

    def test_has_detail_aprovar_permission_pendente(self, gerente_admin, request_factory, admin_user):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.PENDENTE_APROVACAO)
        request = request_factory.get("/")
        request.user = admin_user
        assert gerente_admin.has_detail_aprovar_permission(request, ordem.pk) is True

    def test_has_detail_aprovar_permission_aprovada(self, gerente_admin, request_factory, admin_user):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.APROVADA)
        request = request_factory.get("/")
        request.user = admin_user
        assert gerente_admin.has_detail_aprovar_permission(request, ordem.pk) is False

    def test_has_detail_aprovar_permission_ordem_inexistente(self, gerente_admin, request_factory, admin_user):
        request = request_factory.get("/")
        request.user = admin_user
        assert gerente_admin.has_detail_aprovar_permission(request, 99999) is False

    def test_has_detail_rejeitar_permission_pendente(self, gerente_admin, request_factory, admin_user):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.PENDENTE_APROVACAO)
        request = request_factory.get("/")
        request.user = admin_user
        assert gerente_admin.has_detail_rejeitar_permission(request, ordem.pk) is True

    def test_has_detail_rejeitar_permission_aprovada(self, gerente_admin, request_factory, admin_user):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.APROVADA)
        request = request_factory.get("/")
        request.user = admin_user
        assert gerente_admin.has_detail_rejeitar_permission(request, ordem.pk) is False

    def test_has_detail_faturar_permission_aprovada(self, gerente_admin, request_factory, admin_user):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.APROVADA)
        request = request_factory.get("/")
        request.user = admin_user
        assert gerente_admin.has_detail_faturar_permission(request, ordem.pk) is True

    def test_has_detail_faturar_permission_pendente(self, gerente_admin, request_factory, admin_user):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.PENDENTE_APROVACAO)
        request = request_factory.get("/")
        request.user = admin_user
        assert gerente_admin.has_detail_faturar_permission(request, ordem.pk) is False

    def test_has_detail_concluir_permission_faturada(self, gerente_admin, request_factory, admin_user):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.FATURADA)
        request = request_factory.get("/")
        request.user = admin_user
        assert gerente_admin.has_detail_concluir_permission(request, ordem.pk) is True

    def test_has_detail_concluir_permission_aprovada(self, gerente_admin, request_factory, admin_user):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.APROVADA)
        request = request_factory.get("/")
        request.user = admin_user
        assert gerente_admin.has_detail_concluir_permission(request, ordem.pk) is False

    def test_has_detail_cancelar_permission_pendente(self, gerente_admin, request_factory, admin_user):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.PENDENTE_APROVACAO)
        request = request_factory.get("/")
        request.user = admin_user
        assert gerente_admin.has_detail_cancelar_permission(request, ordem.pk) is True

    def test_has_detail_cancelar_permission_aprovada(self, gerente_admin, request_factory, admin_user):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.APROVADA)
        request = request_factory.get("/")
        request.user = admin_user
        assert gerente_admin.has_detail_cancelar_permission(request, ordem.pk) is True

    def test_has_detail_cancelar_permission_faturada(self, gerente_admin, request_factory, admin_user):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.FATURADA)
        request = request_factory.get("/")
        request.user = admin_user
        assert gerente_admin.has_detail_cancelar_permission(request, ordem.pk) is False


@pytest.mark.django_db
class TestOrdemCompraGerenteAdminDisplayMethods:
    """Testes para metodos de display."""

    def test_get_valor_total(self, gerente_admin):
        ordem = OrdemCompraFactory(valor_total=Decimal("1234.56"))
        resultado = gerente_admin.get_valor_total(ordem)
        assert "1.234,56" in resultado

    def test_get_status_badge_pendente(self, gerente_admin):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.PENDENTE_APROVACAO)
        resultado = gerente_admin.get_status_badge(ordem)
        assert "Pendente de Aprovacao" in resultado or "Pendente" in resultado
        assert "#f59e0b" in resultado  # amber color

    def test_get_status_badge_aprovada(self, gerente_admin):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.APROVADA)
        resultado = gerente_admin.get_status_badge(ordem)
        assert "#10b981" in resultado  # green color

    def test_get_status_badge_rejeitada(self, gerente_admin):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.REJEITADA, motivo_rejeicao="Teste")
        resultado = gerente_admin.get_status_badge(ordem)
        assert "#ef4444" in resultado  # red color

    def test_get_status_badge_faturada(self, gerente_admin):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.FATURADA)
        resultado = gerente_admin.get_status_badge(ordem)
        assert "#3b82f6" in resultado  # blue color

    def test_get_status_badge_concluida(self, gerente_admin):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.CONCLUIDA)
        resultado = gerente_admin.get_status_badge(ordem)
        assert "#6366f1" in resultado  # indigo color

    def test_get_status_badge_cancelada(self, gerente_admin):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.CANCELADA)
        resultado = gerente_admin.get_status_badge(ordem)
        assert "#6b7280" in resultado  # gray color


@pytest.mark.django_db
class TestItemOrdemCompraInlines:
    """Testes para os inlines de itens."""

    def test_gerente_inline_has_add_permission_retorna_false(self, request_factory, admin_user):
        inline = ItemOrdemCompraGerenteInline(OrdemCompra, gerente_site)
        request = request_factory.get("/")
        request.user = admin_user
        assert inline.has_add_permission(request) is False

    def test_gerente_inline_get_subtotal(self):
        inline = ItemOrdemCompraGerenteInline(OrdemCompra, gerente_site)
        item = ItemOrdemCompraFactory(quantidade=3, preco_unitario=Decimal("100.00"))
        resultado = inline.get_subtotal(item)
        assert "300,00" in resultado

    def test_padrao_inline_has_add_permission_retorna_false(self, admin_site, request_factory, admin_user):
        inline = ItemOrdemCompraInline(OrdemCompra, admin_site)
        request = request_factory.get("/")
        request.user = admin_user
        assert inline.has_add_permission(request) is False

    def test_padrao_inline_get_subtotal(self, admin_site):
        inline = ItemOrdemCompraInline(OrdemCompra, admin_site)
        item = ItemOrdemCompraFactory(quantidade=2, preco_unitario=Decimal("50.00"))
        resultado = inline.get_subtotal(item)
        assert "100,00" in resultado


@pytest.mark.django_db
class TestOrdemCompraAdminDisplayMethods:
    """Testes para metodos de display do admin padrao."""

    def test_get_valor_total(self, admin_site):
        admin = OrdemCompraAdmin(OrdemCompra, admin_site)
        ordem = OrdemCompraFactory(valor_total=Decimal("999.99"))
        resultado = admin.get_valor_total(ordem)
        assert "999,99" in resultado

    def test_get_status_badge(self, admin_site):
        admin = OrdemCompraAdmin(OrdemCompra, admin_site)
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.APROVADA)
        resultado = admin.get_status_badge(ordem)
        assert "#10b981" in resultado


@pytest.mark.django_db
class TestOrdemCompraAdminListActions:
    """Testes para acoes de lista."""

    def test_action_aprovar_sucesso(self, admin_site, request_factory, admin_user):
        admin = OrdemCompraAdmin(OrdemCompra, admin_site)
        ordem1 = OrdemCompraFactory(status=StatusOrdemCompra.PENDENTE_APROVACAO)
        ordem2 = OrdemCompraFactory(status=StatusOrdemCompra.PENDENTE_APROVACAO)
        queryset = OrdemCompra.objects.filter(pk__in=[ordem1.pk, ordem2.pk])

        request = request_factory.post("/")
        request.user = admin_user
        request._messages = MockMessages()

        admin.action_aprovar(request, queryset)

        ordem1.refresh_from_db()
        ordem2.refresh_from_db()
        assert ordem1.status == StatusOrdemCompra.APROVADA
        assert ordem2.status == StatusOrdemCompra.APROVADA

    def test_action_aprovar_com_erro(self, admin_site, request_factory, admin_user):
        admin = OrdemCompraAdmin(OrdemCompra, admin_site)
        ordem_pendente = OrdemCompraFactory(status=StatusOrdemCompra.PENDENTE_APROVACAO)
        ordem_aprovada = OrdemCompraFactory(status=StatusOrdemCompra.APROVADA)
        queryset = OrdemCompra.objects.filter(pk__in=[ordem_pendente.pk, ordem_aprovada.pk])

        request = request_factory.post("/")
        request.user = admin_user
        request._messages = MockMessages()

        admin.action_aprovar(request, queryset)

        ordem_pendente.refresh_from_db()
        ordem_aprovada.refresh_from_db()
        assert ordem_pendente.status == StatusOrdemCompra.APROVADA
        assert ordem_aprovada.status == StatusOrdemCompra.APROVADA  # ja estava

    def test_action_faturar_sucesso(self, admin_site, request_factory, admin_user):
        admin = OrdemCompraAdmin(OrdemCompra, admin_site)
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.APROVADA)
        queryset = OrdemCompra.objects.filter(pk=ordem.pk)

        request = request_factory.post("/")
        request.user = admin_user
        request._messages = MockMessages()

        admin.action_faturar(request, queryset)

        ordem.refresh_from_db()
        assert ordem.status == StatusOrdemCompra.FATURADA

    def test_action_faturar_com_erro(self, admin_site, request_factory, admin_user):
        admin = OrdemCompraAdmin(OrdemCompra, admin_site)
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.PENDENTE_APROVACAO)
        queryset = OrdemCompra.objects.filter(pk=ordem.pk)

        request = request_factory.post("/")
        request.user = admin_user
        request._messages = MockMessages()

        admin.action_faturar(request, queryset)

        ordem.refresh_from_db()
        assert ordem.status == StatusOrdemCompra.PENDENTE_APROVACAO  # nao mudou


@pytest.mark.django_db
class TestOrdemCompraGerenteAdminListActions:
    """Testes para acoes de lista do admin de gerentes."""

    def test_action_aprovar_sucesso(self, gerente_admin, request_factory, admin_user):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.PENDENTE_APROVACAO)
        queryset = OrdemCompra.objects.filter(pk=ordem.pk)

        request = request_factory.post("/")
        request.user = admin_user
        request._messages = MockMessages()

        gerente_admin.action_aprovar(request, queryset)

        ordem.refresh_from_db()
        assert ordem.status == StatusOrdemCompra.APROVADA

    def test_action_aprovar_com_erro(self, gerente_admin, request_factory, admin_user):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.APROVADA)
        queryset = OrdemCompra.objects.filter(pk=ordem.pk)

        request = request_factory.post("/")
        request.user = admin_user
        request._messages = MockMessages()

        gerente_admin.action_aprovar(request, queryset)

        # Verifica que mensagem de erro foi adicionada
        assert len(request._messages.messages) > 0

    def test_action_faturar_sucesso(self, gerente_admin, request_factory, admin_user):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.APROVADA)
        queryset = OrdemCompra.objects.filter(pk=ordem.pk)

        request = request_factory.post("/")
        request.user = admin_user
        request._messages = MockMessages()

        gerente_admin.action_faturar(request, queryset)

        ordem.refresh_from_db()
        assert ordem.status == StatusOrdemCompra.FATURADA

    def test_action_faturar_com_erro(self, gerente_admin, request_factory, admin_user):
        ordem = OrdemCompraFactory(status=StatusOrdemCompra.PENDENTE_APROVACAO)
        queryset = OrdemCompra.objects.filter(pk=ordem.pk)

        request = request_factory.post("/")
        request.user = admin_user
        request._messages = MockMessages()

        gerente_admin.action_faturar(request, queryset)

        ordem.refresh_from_db()
        assert ordem.status == StatusOrdemCompra.PENDENTE_APROVACAO  # nao mudou


class MockMessages:
    """Mock para o sistema de mensagens do Django."""

    def __init__(self):
        self.messages = []

    def add(self, level, message, extra_tags=""):
        self.messages.append({"level": level, "message": message})
