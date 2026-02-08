"""
Testes para os mixins de admin com suporte a multitenancy.

Usa modelos reais do sistema (Inventario) para testar o comportamento.
"""
import pytest
from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from plataforma_de_servicos.core.admin.mixins import TenantAwareAdminMixin
from plataforma_de_servicos.empresa.tests.factories.empresa_factory import EmpresaFactory
from plataforma_de_servicos.inventario.models import Inventario

User = get_user_model()


class InventarioTestAdmin(TenantAwareAdminMixin, admin.ModelAdmin):
    """Admin de teste para Inventario."""
    pass


@pytest.fixture
def empresa_a():
    return EmpresaFactory(nome="Empresa A")


@pytest.fixture
def empresa_b():
    return EmpresaFactory(nome="Empresa B")


@pytest.fixture
def superuser():
    return User.objects.create_superuser("superuser@example.com", "password")


@pytest.fixture
def gerente_user(empresa_a):
    user = User.objects.create_user("gerente@example.com", "password")
    return user


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def gerente_admin_site():
    """Simula o admin site de gerentes."""
    site = admin.AdminSite(name="gerentes")
    return site


@pytest.fixture
def main_admin_site():
    """Admin site principal."""
    site = admin.AdminSite(name="admin")
    return site


@pytest.mark.django_db
class TestTenantAwareAdminMixin:
    """Testes para TenantAwareAdminMixin usando modelo Inventario."""

    def test_get_queryset_gerente_admin_with_tenant(
        self, empresa_a, gerente_user, request_factory, gerente_admin_site
    ):
        """No admin de gerentes com tenant, filtra por empresa."""
        inv_a = Inventario.objects.create(nome="Inventario A", empresa=empresa_a)

        model_admin = InventarioTestAdmin(Inventario, gerente_admin_site)
        request = request_factory.get("/")
        request.user = gerente_user
        request.tenant = empresa_a

        qs = model_admin.get_queryset(request)

        assert qs.count() == 1
        assert qs.first() == inv_a

    def test_get_queryset_gerente_admin_no_tenant_returns_empty(
        self, empresa_a, gerente_user, request_factory, gerente_admin_site
    ):
        """No admin de gerentes sem tenant, retorna queryset vazio."""
        Inventario.objects.create(nome="Inventario A", empresa=empresa_a)

        model_admin = InventarioTestAdmin(Inventario, gerente_admin_site)
        request = request_factory.get("/")
        request.user = gerente_user
        request.tenant = None

        qs = model_admin.get_queryset(request)

        assert qs.count() == 0

    def test_get_queryset_gerente_admin_isolates_tenants(
        self, empresa_a, empresa_b, gerente_user, request_factory, gerente_admin_site
    ):
        """No admin de gerentes, cada tenant só vê seus próprios dados."""
        inv_a = Inventario.objects.create(nome="Inventario A", empresa=empresa_a)
        Inventario.objects.create(nome="Inventario B", empresa=empresa_b)

        model_admin = InventarioTestAdmin(Inventario, gerente_admin_site)
        request = request_factory.get("/")
        request.user = gerente_user
        request.tenant = empresa_a

        qs = model_admin.get_queryset(request)

        assert qs.count() == 1
        assert inv_a in qs

    def test_get_queryset_main_admin_superuser_sees_all(
        self, empresa_a, empresa_b, superuser, request_factory, main_admin_site
    ):
        """No admin principal, superusuário sem tenant vê tudo."""
        Inventario.objects.create(nome="Inventario A", empresa=empresa_a)
        Inventario.objects.create(nome="Inventario B", empresa=empresa_b)

        model_admin = InventarioTestAdmin(Inventario, main_admin_site)
        request = request_factory.get("/")
        request.user = superuser
        request.tenant = None

        qs = model_admin.get_queryset(request)

        assert qs.count() == 2

    def test_get_queryset_main_admin_with_tenant_filters(
        self, empresa_a, empresa_b, gerente_user, request_factory, main_admin_site
    ):
        """No admin principal com tenant definido, filtra por empresa."""
        inv_a = Inventario.objects.create(nome="Inventario A", empresa=empresa_a)
        Inventario.objects.create(nome="Inventario B", empresa=empresa_b)

        model_admin = InventarioTestAdmin(Inventario, main_admin_site)
        request = request_factory.get("/")
        request.user = gerente_user
        request.tenant = empresa_a

        qs = model_admin.get_queryset(request)

        assert qs.count() == 1
        assert qs.first() == inv_a

    def test_save_model_auto_fills_empresa(
        self, empresa_a, gerente_user, request_factory, gerente_admin_site
    ):
        """Ao criar objeto, auto-preenche empresa do tenant."""
        model_admin = InventarioTestAdmin(Inventario, gerente_admin_site)
        request = request_factory.post("/")
        request.user = gerente_user
        request.tenant = empresa_a

        new_inv = Inventario(nome="Novo Inventario")
        model_admin.save_model(request, new_inv, None, change=False)

        assert new_inv.empresa == empresa_a
        assert new_inv.pk is not None

    def test_save_model_does_not_override_existing_empresa(
        self, empresa_a, empresa_b, gerente_user, request_factory, gerente_admin_site
    ):
        """Ao editar objeto, não sobrescreve empresa existente."""
        existing_inv = Inventario.objects.create(nome="Existente", empresa=empresa_b)

        model_admin = InventarioTestAdmin(Inventario, gerente_admin_site)
        request = request_factory.post("/")
        request.user = gerente_user
        request.tenant = empresa_a

        existing_inv.nome = "Editado"
        model_admin.save_model(request, existing_inv, None, change=True)

        existing_inv.refresh_from_db()
        # Empresa não deve mudar em edição
        assert existing_inv.empresa == empresa_b

    def test_get_form_hides_empresa_in_gerente_admin(
        self, empresa_a, gerente_user, request_factory, gerente_admin_site
    ):
        """No admin de gerentes, campo empresa é hidden e auto-preenchido."""
        model_admin = InventarioTestAdmin(Inventario, gerente_admin_site)
        request = request_factory.get("/")
        request.user = gerente_user
        request.tenant = empresa_a

        form_class = model_admin.get_form(request)
        form = form_class()

        assert "empresa" in form.base_fields
        assert isinstance(form.base_fields["empresa"].widget, forms.HiddenInput)
        assert form.base_fields["empresa"].initial == empresa_a
        assert not form.base_fields["empresa"].required

    def test_get_form_shows_empresa_for_superuser_in_main_admin(
        self, superuser, request_factory, main_admin_site
    ):
        """No admin principal, superusuário vê campo empresa."""
        model_admin = InventarioTestAdmin(Inventario, main_admin_site)
        request = request_factory.get("/")
        request.user = superuser
        request.tenant = None

        form_class = model_admin.get_form(request)
        form = form_class()

        assert "empresa" in form.base_fields
        # Para superusuário sem tenant, widget não deve ser hidden
        assert not isinstance(form.base_fields["empresa"].widget, forms.HiddenInput)

    def test_is_gerente_admin_returns_true_for_gerentes_site(
        self, gerente_admin_site
    ):
        """_is_gerente_admin retorna True para site de gerentes."""
        model_admin = InventarioTestAdmin(Inventario, gerente_admin_site)

        assert model_admin._is_gerente_admin() is True

    def test_is_gerente_admin_returns_false_for_main_site(
        self, main_admin_site
    ):
        """_is_gerente_admin retorna False para site principal."""
        model_admin = InventarioTestAdmin(Inventario, main_admin_site)

        assert model_admin._is_gerente_admin() is False
