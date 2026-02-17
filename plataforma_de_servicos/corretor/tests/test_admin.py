from unittest.mock import Mock

import pytest
from django.contrib.admin.sites import AdminSite

from plataforma_de_servicos.corretor.admin import InteresseCompraAdmin
from plataforma_de_servicos.corretor.admin.gerente_admin import InteresseCompraGerenteAdmin
from plataforma_de_servicos.corretor.models import InteresseCompra
from plataforma_de_servicos.corretor.models import StatusInteresse
from plataforma_de_servicos.corretor.tests.factories import InteresseCompraFactory
from plataforma_de_servicos.users.tests.factories import UserFactory

pytestmark = [pytest.mark.django_db]


class TestInteresseCompraAdmin:
    """Testes para o admin de InteresseCompra."""

    def test_list_display(self):
        """Verifica campos exibidos na listagem."""
        admin = InteresseCompraAdmin(InteresseCompra, AdminSite())
        expected_fields = ["id", "nome_cliente", "email_cliente", "valor_total", "status"]
        for field in expected_fields:
            assert field in admin.list_display

    def test_list_display_links(self):
        """Verifica campos clicáveis na listagem."""
        admin = InteresseCompraAdmin(InteresseCompra, AdminSite())
        assert "id" in admin.list_display_links
        assert "nome_cliente" in admin.list_display_links

    def test_readonly_fields_dados_cliente(self):
        """Dados do cliente devem ser somente leitura."""
        admin = InteresseCompraAdmin(InteresseCompra, AdminSite())
        campos_cliente = ["nome_cliente", "email_cliente", "telefone_cliente", "mensagem"]
        for campo in campos_cliente:
            assert campo in admin.readonly_fields, f"{campo} deve ser readonly"

    def test_readonly_fields_valor(self):
        """Valor total deve ser somente leitura."""
        admin = InteresseCompraAdmin(InteresseCompra, AdminSite())
        assert "valor_total" in admin.readonly_fields

    def test_readonly_fields_timestamps(self):
        """Timestamps devem ser somente leitura."""
        admin = InteresseCompraAdmin(InteresseCompra, AdminSite())
        assert "created" in admin.readonly_fields
        assert "modified" in admin.readonly_fields

    def test_campos_editaveis(self):
        """Apenas status e corretor devem ser editáveis."""
        admin = InteresseCompraAdmin(InteresseCompra, AdminSite())
        # Esses campos NÃO devem estar em readonly
        assert "status" not in admin.readonly_fields
        assert "corretor" not in admin.readonly_fields

    def test_autocomplete_fields(self):
        """Corretor deve ter autocomplete."""
        admin = InteresseCompraAdmin(InteresseCompra, AdminSite())
        assert "corretor" in admin.autocomplete_fields

    def test_inlines_configurado(self):
        """Deve ter inline de itens."""
        admin = InteresseCompraAdmin(InteresseCompra, AdminSite())
        assert len(admin.inlines) == 1
        inline_class = admin.inlines[0]
        assert inline_class.model.__name__ == "ItemInteresse"

    def test_search_fields(self):
        """Verifica campos de busca."""
        admin = InteresseCompraAdmin(InteresseCompra, AdminSite())
        assert "nome_cliente" in admin.search_fields
        assert "email_cliente" in admin.search_fields
        assert "telefone_cliente" in admin.search_fields

    def test_list_filter(self):
        """Verifica filtros da listagem."""
        admin = InteresseCompraAdmin(InteresseCompra, AdminSite())
        assert "status" in admin.list_filter
        assert "corretor" in admin.list_filter
        assert "created" in admin.list_filter


class TestInteresseCompraGerenteAdmin:
    """Testes para o admin de InteresseCompra no site de gerentes."""

    def test_readonly_fields_dados_cliente(self):
        """Dados do cliente devem ser somente leitura."""
        admin = InteresseCompraGerenteAdmin(InteresseCompra, AdminSite())
        campos_cliente = ["nome_cliente", "email_cliente", "telefone_cliente", "mensagem"]
        for campo in campos_cliente:
            assert campo in admin.readonly_fields, f"{campo} deve ser readonly"

    def test_readonly_fields_valor(self):
        """Valor total deve ser somente leitura."""
        admin = InteresseCompraGerenteAdmin(InteresseCompra, AdminSite())
        assert "valor_total" in admin.readonly_fields

    def test_list_display_links(self):
        """Verifica campos clicáveis na listagem."""
        admin = InteresseCompraGerenteAdmin(InteresseCompra, AdminSite())
        assert "numero" in admin.list_display_links
        assert "nome_cliente" in admin.list_display_links

    def test_autocomplete_fields(self):
        """Corretor deve ter autocomplete."""
        admin = InteresseCompraGerenteAdmin(InteresseCompra, AdminSite())
        assert "corretor" in admin.autocomplete_fields

    def test_campos_editaveis(self):
        """Status é readonly (gerenciado por botões), corretor editável apenas em atendimento."""
        admin = InteresseCompraGerenteAdmin(InteresseCompra, AdminSite())
        # Status agora é gerenciado pelos actions_detail (botões)
        assert "status" in admin.readonly_fields
        # Corretor não está na lista base de readonly (pode ser editável em atendimento)
        assert "corretor" not in admin.readonly_fields


class TestInteresseCompraGerenteAdminReadonlyFields:
    """Testes para o método get_readonly_fields do admin de gerentes."""

    def setup_method(self):
        """Setup comum para os testes."""
        self.admin = InteresseCompraGerenteAdmin(InteresseCompra, AdminSite())

    def _make_request(self, is_superuser: bool):
        """Cria um request mock com usuário."""
        request = Mock()
        request.user = Mock()
        request.user.is_superuser = is_superuser
        return request

    def test_superusuario_pode_editar_corretor_status_novo(self):
        """Superusuário pode editar corretor mesmo com status NOVO."""
        interesse = InteresseCompraFactory(status=StatusInteresse.NOVO)
        request = self._make_request(is_superuser=True)

        readonly = self.admin.get_readonly_fields(request, interesse)

        assert "corretor" not in readonly

    def test_superusuario_pode_editar_corretor_status_em_atendimento(self):
        """Superusuário pode editar corretor com status EM_ATENDIMENTO."""
        interesse = InteresseCompraFactory(status=StatusInteresse.EM_ATENDIMENTO)
        request = self._make_request(is_superuser=True)

        readonly = self.admin.get_readonly_fields(request, interesse)

        assert "corretor" not in readonly

    def test_superusuario_pode_editar_corretor_status_convertido(self):
        """Superusuário pode editar corretor mesmo com status CONVERTIDO."""
        interesse = InteresseCompraFactory(status=StatusInteresse.CONVERTIDO)
        request = self._make_request(is_superuser=True)

        readonly = self.admin.get_readonly_fields(request, interesse)

        assert "corretor" not in readonly

    def test_superusuario_pode_editar_corretor_status_descartado(self):
        """Superusuário pode editar corretor mesmo com status DESCARTADO."""
        interesse = InteresseCompraFactory(status=StatusInteresse.DESCARTADO)
        request = self._make_request(is_superuser=True)

        readonly = self.admin.get_readonly_fields(request, interesse)

        assert "corretor" not in readonly

    def test_usuario_normal_nao_pode_editar_corretor_status_novo(self):
        """Usuário normal NÃO pode editar corretor com status NOVO."""
        interesse = InteresseCompraFactory(status=StatusInteresse.NOVO)
        request = self._make_request(is_superuser=False)

        readonly = self.admin.get_readonly_fields(request, interesse)

        assert "corretor" in readonly

    def test_usuario_normal_pode_editar_corretor_status_em_atendimento(self):
        """Usuário normal pode editar corretor com status EM_ATENDIMENTO."""
        interesse = InteresseCompraFactory(status=StatusInteresse.EM_ATENDIMENTO)
        request = self._make_request(is_superuser=False)

        readonly = self.admin.get_readonly_fields(request, interesse)

        assert "corretor" not in readonly

    def test_usuario_normal_nao_pode_editar_corretor_status_convertido(self):
        """Usuário normal NÃO pode editar corretor com status CONVERTIDO."""
        interesse = InteresseCompraFactory(status=StatusInteresse.CONVERTIDO)
        request = self._make_request(is_superuser=False)

        readonly = self.admin.get_readonly_fields(request, interesse)

        assert "corretor" in readonly

    def test_usuario_normal_nao_pode_editar_corretor_status_descartado(self):
        """Usuário normal NÃO pode editar corretor com status DESCARTADO."""
        interesse = InteresseCompraFactory(status=StatusInteresse.DESCARTADO)
        request = self._make_request(is_superuser=False)

        readonly = self.admin.get_readonly_fields(request, interesse)

        assert "corretor" in readonly

    def test_readonly_fields_sem_objeto(self):
        """Sem objeto (criação), retorna readonly_fields base."""
        request = self._make_request(is_superuser=False)

        readonly = self.admin.get_readonly_fields(request, obj=None)

        # Corretor não deve estar em readonly quando não há objeto
        assert "corretor" not in readonly


class TestInteresseCompraGerenteAdminStatusBadge:
    """Testes para o badge de status no admin."""

    def setup_method(self):
        """Setup comum para os testes."""
        self.admin = InteresseCompraGerenteAdmin(InteresseCompra, AdminSite())

    def test_badge_status_novo(self):
        """Badge de status NOVO deve ser azul."""
        interesse = InteresseCompraFactory(status=StatusInteresse.NOVO)

        badge_html = self.admin.get_status_badge(interesse)

        assert "#3b82f6" in badge_html  # blue
        assert "Novo" in badge_html

    def test_badge_status_em_atendimento(self):
        """Badge de status EM_ATENDIMENTO deve ser âmbar."""
        interesse = InteresseCompraFactory(status=StatusInteresse.EM_ATENDIMENTO)

        badge_html = self.admin.get_status_badge(interesse)

        assert "#f59e0b" in badge_html  # amber
        assert "Em Atendimento" in badge_html

    def test_badge_status_convertido(self):
        """Badge de status CONVERTIDO deve ser verde."""
        interesse = InteresseCompraFactory(status=StatusInteresse.CONVERTIDO)

        badge_html = self.admin.get_status_badge(interesse)

        assert "#10b981" in badge_html  # green
        assert "Convertido" in badge_html

    def test_badge_status_descartado(self):
        """Badge de status DESCARTADO deve ser cinza."""
        interesse = InteresseCompraFactory(status=StatusInteresse.DESCARTADO)

        badge_html = self.admin.get_status_badge(interesse)

        assert "#6b7280" in badge_html  # gray
        assert "Descartado" in badge_html


class TestInteresseCompraGerenteAdminPermissions:
    """Testes para os métodos de permissão das ações de detalhe."""

    def setup_method(self):
        """Setup comum para os testes."""
        self.admin = InteresseCompraGerenteAdmin(InteresseCompra, AdminSite())
        self.request = Mock()

    def test_has_detail_atender_permission_status_novo(self):
        """Pode atender quando status é NOVO."""
        interesse = InteresseCompraFactory(status=StatusInteresse.NOVO)

        result = self.admin.has_detail_atender_permission(self.request, interesse.pk)

        assert result is True

    def test_has_detail_atender_permission_status_em_atendimento(self):
        """Não pode atender quando já está em atendimento."""
        interesse = InteresseCompraFactory(status=StatusInteresse.EM_ATENDIMENTO)

        result = self.admin.has_detail_atender_permission(self.request, interesse.pk)

        assert result is False

    def test_has_detail_atender_permission_interesse_inexistente(self):
        """Retorna False para interesse inexistente."""
        result = self.admin.has_detail_atender_permission(self.request, 99999)

        assert result is False

    def test_has_detail_converter_permission_status_em_atendimento(self):
        """Pode converter quando status é EM_ATENDIMENTO."""
        interesse = InteresseCompraFactory(status=StatusInteresse.EM_ATENDIMENTO)

        result = self.admin.has_detail_converter_permission(self.request, interesse.pk)

        assert result is True

    def test_has_detail_converter_permission_status_novo(self):
        """Não pode converter quando status é NOVO."""
        interesse = InteresseCompraFactory(status=StatusInteresse.NOVO)

        result = self.admin.has_detail_converter_permission(self.request, interesse.pk)

        assert result is False

    def test_has_detail_converter_permission_interesse_inexistente(self):
        """Retorna False para interesse inexistente."""
        result = self.admin.has_detail_converter_permission(self.request, 99999)

        assert result is False

    def test_has_detail_descartar_permission_status_novo(self):
        """Pode descartar quando status é NOVO."""
        interesse = InteresseCompraFactory(status=StatusInteresse.NOVO)

        result = self.admin.has_detail_descartar_permission(self.request, interesse.pk)

        assert result is True

    def test_has_detail_descartar_permission_status_em_atendimento(self):
        """Pode descartar quando status é EM_ATENDIMENTO."""
        interesse = InteresseCompraFactory(status=StatusInteresse.EM_ATENDIMENTO)

        result = self.admin.has_detail_descartar_permission(self.request, interesse.pk)

        assert result is True

    def test_has_detail_descartar_permission_status_convertido(self):
        """Não pode descartar quando já foi convertido."""
        interesse = InteresseCompraFactory(status=StatusInteresse.CONVERTIDO)

        result = self.admin.has_detail_descartar_permission(self.request, interesse.pk)

        assert result is False

    def test_has_detail_descartar_permission_interesse_inexistente(self):
        """Retorna False para interesse inexistente."""
        result = self.admin.has_detail_descartar_permission(self.request, 99999)

        assert result is False

    def test_has_detail_retornar_permission_status_em_atendimento(self):
        """Pode retornar quando status é EM_ATENDIMENTO."""
        interesse = InteresseCompraFactory(status=StatusInteresse.EM_ATENDIMENTO)

        result = self.admin.has_detail_retornar_permission(self.request, interesse.pk)

        assert result is True

    def test_has_detail_retornar_permission_status_novo(self):
        """Não pode retornar quando status é NOVO."""
        interesse = InteresseCompraFactory(status=StatusInteresse.NOVO)

        result = self.admin.has_detail_retornar_permission(self.request, interesse.pk)

        assert result is False

    def test_has_detail_retornar_permission_interesse_inexistente(self):
        """Retorna False para interesse inexistente."""
        result = self.admin.has_detail_retornar_permission(self.request, 99999)

        assert result is False


