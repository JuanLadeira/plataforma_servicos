import pytest
from django.contrib.admin.sites import AdminSite

from plataforma_de_servicos.corretor.admin import InteresseCompraAdmin
from plataforma_de_servicos.corretor.admin.gerente_admin import InteresseCompraGerenteAdmin
from plataforma_de_servicos.corretor.models import InteresseCompra

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
