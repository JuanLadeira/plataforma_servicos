import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from plataforma_de_servicos.estoque.admin.gerente_admin import EstoqueEntradaAdmin
from plataforma_de_servicos.estoque.admin.gerente_admin import EstoqueItensInline
from plataforma_de_servicos.estoque.admin.gerente_admin import EstoqueSaidaAdmin
from plataforma_de_servicos.estoque.models.proxys.estoque_entrada import EstoqueEntrada
from plataforma_de_servicos.estoque.models.proxys.estoque_saida import EstoqueSaida
from plataforma_de_servicos.inventario.tests.factories import InventarioFactory
from plataforma_de_servicos.users.tests.factories import UserFactory


@pytest.fixture
def admin_site():
    return AdminSite()


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def admin_user():
    return UserFactory(is_staff=True, is_superuser=True)


@pytest.fixture
def inventario():
    return InventarioFactory()


@pytest.mark.django_db
class TestEstoqueEntradaAdminReadOnly:
    """Testes para verificar comportamento read-only após criação."""

    def test_get_readonly_fields_sem_obj_retorna_vazio(self, admin_site, request_factory, admin_user):
        """Na criação (sem obj), não há campos readonly extras."""
        admin = EstoqueEntradaAdmin(EstoqueEntrada, admin_site)
        request = request_factory.get("/")
        request.user = admin_user
        readonly = admin.get_readonly_fields(request, obj=None)
        assert readonly == ()

    def test_get_readonly_fields_com_obj_retorna_campos(self, admin_site, request_factory, admin_user, inventario):
        """Na edição (com obj), retorna campos readonly."""
        admin = EstoqueEntradaAdmin(EstoqueEntrada, admin_site)
        request = request_factory.get("/")
        request.user = admin_user

        entrada = EstoqueEntrada.objects.create(
            funcionario=admin_user,
            movimento="E",
            inventario_destino=inventario,
        )

        readonly = admin.get_readonly_fields(request, obj=entrada)
        assert "inventario_destino" in readonly
        assert "funcionario" in readonly
        assert "observacao" in readonly

    def test_get_readonly_fields_nf_vazia_editavel(self, admin_site, request_factory, admin_user, inventario):
        """Se NF está vazia (None), ela não está nos campos readonly."""
        admin = EstoqueEntradaAdmin(EstoqueEntrada, admin_site)
        request = request_factory.get("/")
        request.user = admin_user

        entrada = EstoqueEntrada.objects.create(
            funcionario=admin_user,
            movimento="E",
            inventario_destino=inventario,
            nf=None,
        )

        readonly = admin.get_readonly_fields(request, obj=entrada)
        assert "nf" not in readonly

    def test_get_readonly_fields_nf_preenchida_readonly(self, admin_site, request_factory, admin_user, inventario):
        """Se NF está preenchida, ela está nos campos readonly."""
        admin = EstoqueEntradaAdmin(EstoqueEntrada, admin_site)
        request = request_factory.get("/")
        request.user = admin_user

        entrada = EstoqueEntrada.objects.create(
            funcionario=admin_user,
            movimento="E",
            inventario_destino=inventario,
            nf=12345,
        )

        readonly = admin.get_readonly_fields(request, obj=entrada)
        assert "nf" in readonly

    def test_has_delete_permission_sem_obj_retorna_true(self, admin_site, request_factory, admin_user):
        """Na criação, permite deletar."""
        admin = EstoqueEntradaAdmin(EstoqueEntrada, admin_site)
        request = request_factory.get("/")
        request.user = admin_user
        assert admin.has_delete_permission(request, obj=None) is True

    def test_has_delete_permission_com_obj_retorna_false(self, admin_site, request_factory, admin_user, inventario):
        """Na edição, não permite deletar."""
        admin = EstoqueEntradaAdmin(EstoqueEntrada, admin_site)
        request = request_factory.get("/")
        request.user = admin_user

        entrada = EstoqueEntrada.objects.create(
            funcionario=admin_user,
            movimento="E",
            inventario_destino=inventario,
        )

        assert admin.has_delete_permission(request, obj=entrada) is False


@pytest.mark.django_db
class TestEstoqueSaidaAdminReadOnly:
    """Testes para verificar comportamento read-only após criação."""

    def test_get_readonly_fields_sem_obj_retorna_ordem_compra(self, admin_site, request_factory, admin_user):
        """Na criação (sem obj), apenas ordem_compra é readonly."""
        admin = EstoqueSaidaAdmin(EstoqueSaida, admin_site)
        request = request_factory.get("/")
        request.user = admin_user
        readonly = admin.get_readonly_fields(request, obj=None)
        assert "ordem_compra" in readonly

    def test_get_readonly_fields_com_obj_retorna_campos(self, admin_site, request_factory, admin_user, inventario):
        """Na edição (com obj), retorna campos readonly."""
        admin = EstoqueSaidaAdmin(EstoqueSaida, admin_site)
        request = request_factory.get("/")
        request.user = admin_user

        saida = EstoqueSaida.objects.create(
            funcionario=admin_user,
            movimento="S",
            inventario_origem=inventario,
            origem_saida="MA",
        )

        readonly = admin.get_readonly_fields(request, obj=saida)
        assert "inventario_origem" in readonly
        assert "funcionario" in readonly
        assert "origem_saida" in readonly
        assert "observacao" in readonly
        assert "ordem_compra" in readonly

    def test_get_readonly_fields_nf_vazia_editavel(self, admin_site, request_factory, admin_user, inventario):
        """Se NF está vazia (None), permite editar (para saídas automáticas)."""
        admin = EstoqueSaidaAdmin(EstoqueSaida, admin_site)
        request = request_factory.get("/")
        request.user = admin_user

        saida = EstoqueSaida.objects.create(
            funcionario=admin_user,
            movimento="S",
            inventario_origem=inventario,
            origem_saida="PE",
            nf=None,
        )

        readonly = admin.get_readonly_fields(request, obj=saida)
        assert "nf" not in readonly

    def test_get_readonly_fields_nf_preenchida_readonly(self, admin_site, request_factory, admin_user, inventario):
        """Se NF está preenchida, fica readonly."""
        admin = EstoqueSaidaAdmin(EstoqueSaida, admin_site)
        request = request_factory.get("/")
        request.user = admin_user

        saida = EstoqueSaida.objects.create(
            funcionario=admin_user,
            movimento="S",
            inventario_origem=inventario,
            origem_saida="MA",
            nf=67890,
        )

        readonly = admin.get_readonly_fields(request, obj=saida)
        assert "nf" in readonly

    def test_has_delete_permission_com_obj_retorna_false(self, admin_site, request_factory, admin_user, inventario):
        """Na edição, não permite deletar."""
        admin = EstoqueSaidaAdmin(EstoqueSaida, admin_site)
        request = request_factory.get("/")
        request.user = admin_user

        saida = EstoqueSaida.objects.create(
            funcionario=admin_user,
            movimento="S",
            inventario_origem=inventario,
            origem_saida="MA",
        )

        assert admin.has_delete_permission(request, obj=saida) is False


@pytest.mark.django_db
class TestEstoqueItensInlineReadOnly:
    """Testes para verificar que itens ficam readonly após criação do estoque."""

    def test_get_readonly_fields_sem_obj_retorna_minimo(self, admin_site, request_factory, admin_user):
        """Na criação, apenas saldo e inventario são readonly."""
        inline = EstoqueItensInline(EstoqueEntrada, admin_site)
        request = request_factory.get("/")
        request.user = admin_user
        readonly = inline.get_readonly_fields(request, obj=None)
        assert readonly == ("saldo_atual", "saldo_preview", "inventario")

    def test_get_readonly_fields_com_obj_retorna_todos(self, admin_site, request_factory, admin_user, inventario):
        """Na edição, todos os campos são readonly."""
        inline = EstoqueItensInline(EstoqueEntrada, admin_site)
        request = request_factory.get("/")
        request.user = admin_user

        entrada = EstoqueEntrada.objects.create(
            funcionario=admin_user,
            movimento="E",
            inventario_destino=inventario,
        )

        readonly = inline.get_readonly_fields(request, obj=entrada)
        expected_readonly = ("variacao", "quantidade", "saldo_atual", "saldo_preview", "inventario")
        assert all(field in readonly for field in expected_readonly)

    def test_has_add_permission_sem_obj_retorna_true(self, admin_site, request_factory, admin_user):
        """Na criação, permite adicionar itens."""
        inline = EstoqueItensInline(EstoqueEntrada, admin_site)
        request = request_factory.get("/")
        request.user = admin_user
        assert inline.has_add_permission(request, obj=None) is True

    def test_has_add_permission_com_obj_retorna_false(self, admin_site, request_factory, admin_user, inventario):
        """Na edição, não permite adicionar itens."""
        inline = EstoqueItensInline(EstoqueEntrada, admin_site)
        request = request_factory.get("/")
        request.user = admin_user

        entrada = EstoqueEntrada.objects.create(
            funcionario=admin_user,
            movimento="E",
            inventario_destino=inventario,
        )

        assert inline.has_add_permission(request, obj=entrada) is False

    def test_has_delete_permission_sem_obj_retorna_true(self, admin_site, request_factory, admin_user):
        """Na criação, permite deletar itens."""
        inline = EstoqueItensInline(EstoqueEntrada, admin_site)
        request = request_factory.get("/")
        request.user = admin_user
        assert inline.has_delete_permission(request, obj=None) is True

    def test_has_delete_permission_com_obj_retorna_false(self, admin_site, request_factory, admin_user, inventario):
        """Na edição, não permite deletar itens."""
        inline = EstoqueItensInline(EstoqueEntrada, admin_site)
        request = request_factory.get("/")
        request.user = admin_user

        entrada = EstoqueEntrada.objects.create(
            funcionario=admin_user,
            movimento="E",
            inventario_destino=inventario,
        )

        assert inline.has_delete_permission(request, obj=entrada) is False
