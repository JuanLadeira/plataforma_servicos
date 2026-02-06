from decimal import Decimal

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from ..admin.atributos_admin import AtributoAdmin
from ..admin.atributos_admin import ValorAtributoAdmin
from ..admin.gerente_admin import ProdutoGerenteAdmin
from ..admin.gerente_admin import ValorAtributoGerenteAdmin
from ..admin.gerente_admin import VariacaoProdutoInline
from ..models import Atributo
from ..models import ValorAtributo
from ..models import VariacaoProduto
from .factories import AtributoFactory
from .factories import ProdutoFactory
from .factories import ValorAtributoFactory
from .factories import VariacaoProdutoFactory

User = get_user_model()
pytestmark = [pytest.mark.django_db, pytest.mark.produto]


class TestPricingAdminInterface:
    """Testes para mudanças na interface admin relacionadas aos preços"""

    @pytest.fixture
    def admin_site(self):
        return AdminSite()

    @pytest.fixture
    def admin_user(self):
        return User.objects.create_superuser(
            email="admin@test.com",
            name="Admin Test",
            password="testpass123",
        )

    @pytest.fixture
    def request_factory(self):
        return RequestFactory()

    @pytest.fixture
    def admin_request(self, request_factory, admin_user):
        request = request_factory.get("/")
        request.user = admin_user
        return request

    def test_valor_atributo_admin_displays_price_fields(self, admin_site, admin_request):
        """Testa se o admin do ValorAtributo exibe campos de preço"""
        admin_instance = ValorAtributoAdmin(ValorAtributo, admin_site)

        # Verifica se os campos estão na list_display
        assert "preco_adicional" in admin_instance.list_display
        assert "percentual_adicional" in admin_instance.list_display

        # Verifica se estão editáveis inline
        assert "preco_adicional" in admin_instance.list_editable
        assert "percentual_adicional" in admin_instance.list_editable

    def test_valor_atributo_admin_fieldsets(self, admin_site, admin_request):
        """Testa organização dos fieldsets no admin"""
        admin_instance = ValorAtributoAdmin(ValorAtributo, admin_site)

        fieldsets = admin_instance.fieldsets
        assert len(fieldsets) == 2

        # Primeiro fieldset: dados básicos
        atributo_fieldset = fieldsets[0]
        assert "Atributo" in atributo_fieldset[0]
        assert "atributo" in atributo_fieldset[1]["fields"]
        assert "valor" in atributo_fieldset[1]["fields"]

        # Segundo fieldset: modificadores de preço
        pricing_fieldset = fieldsets[1]
        assert "Modificadores de Preço" in pricing_fieldset[0]
        assert "preco_adicional" in pricing_fieldset[1]["fields"]
        assert "percentual_adicional" in pricing_fieldset[1]["fields"]

    def test_valor_atributo_gerente_admin_displays_price_fields(self, admin_site, admin_request):
        """Testa admin do gerente para ValorAtributo"""
        admin_instance = ValorAtributoGerenteAdmin(ValorAtributo, admin_site)

        # Verifica campos na listagem (modificador_display substitui campos individuais)
        assert "atributo" in admin_instance.list_display
        assert "valor" in admin_instance.list_display
        assert "modificador_display" in admin_instance.list_display

        # Verifica que os campos de preço estão nos fieldsets
        all_fields = []
        for fieldset in admin_instance.fieldsets:
            all_fields.extend(fieldset[1]["fields"])
        assert "preco_adicional" in all_fields
        assert "percentual_adicional" in all_fields

    def test_variacao_produto_inline_shows_calculated_price(self, admin_site, admin_request):
        """Testa se o inline da variação mostra preço calculado"""
        # Cria dados de teste
        produto = ProdutoFactory(produto="Produto Teste", preco=Decimal("100.00"))

        # Atributo deve usar a mesma categoria do produto
        cor_attr = AtributoFactory(nome="Cor", categoria=produto.categoria)
        valor_cor = ValorAtributoFactory(
            atributo=cor_attr,
            valor="Premium",
            preco_adicional=Decimal("20.00"),
            percentual_adicional=Decimal("10.00"),
        )

        variacao = VariacaoProdutoFactory(produto=produto, preco=Decimal("100.00"))
        variacao.valores.clear()
        variacao.valores.add(valor_cor)

        # Testa o método preco_final_calculado
        produto_admin = ProdutoGerenteAdmin(produto.__class__, admin_site)
        inline = VariacaoProdutoInline(produto.__class__, admin_site)

        # Verifica se o método está no readonly_fields
        assert "preco_final_calculado" in inline.readonly_fields

        # Testa o cálculo
        preco_display = inline.preco_final_calculado(variacao)
        expected_price = "R$ 130,00"  # 100 + 20 + (100 * 0.10)
        assert preco_display == expected_price

    def test_variacao_produto_inline_no_price_for_new_objects(self, admin_site, admin_request):
        """Testa exibição para objetos novos (sem pk)"""
        inline = VariacaoProdutoInline(VariacaoProduto, admin_site)

        # Mock de objeto sem pk
        class MockVariacao:
            pk = None

        mock_obj = MockVariacao()
        preco_display = inline.preco_final_calculado(mock_obj)
        assert preco_display == "-"

    def test_admin_price_calculation_integration(self, admin_site, admin_request):
        """Teste de integração completo dos preços no admin"""
        # Cria estrutura completa
        produto = ProdutoFactory(produto="Camiseta", preco=Decimal("50.00"))

        # Múltiplos atributos com modificadores (usam categoria do produto)
        cor_attr = AtributoFactory(nome="Cor", categoria=produto.categoria)
        tam_attr = AtributoFactory(nome="Tamanho", categoria=produto.categoria)

        # Cor premium
        cor_premium = ValorAtributoFactory(
            atributo=cor_attr,
            valor="Ouro",
            preco_adicional=Decimal("25.00"),
            percentual_adicional=Decimal("0"),
        )

        # Tamanho especial
        tam_especial = ValorAtributoFactory(
            atributo=tam_attr,
            valor="XXL",
            preco_adicional=Decimal("5.00"),
            percentual_adicional=Decimal("15.00"),
        )

        # Cria variação com múltiplos modificadores
        variacao = VariacaoProdutoFactory(produto=produto, preco=Decimal("50.00"))
        variacao.valores.clear()
        variacao.valores.add(cor_premium, tam_especial)

        # Verifica cálculo através do admin
        inline = VariacaoProdutoInline(produto.__class__, admin_site)
        preco_display = inline.preco_final_calculado(variacao)

        # 50 (base) + 25 (cor) + 5 (tamanho fixo) + 7.50 (15% de 50) = 87.50
        assert preco_display == "R$ 87,50"

    def test_admin_with_zero_price_modifiers(self, admin_site, admin_request):
        """Testa admin com modificadores zerados"""
        produto = ProdutoFactory(produto="Produto Básico", preco=Decimal("30.00"))

        # Atributo deve usar a mesma categoria do produto
        cor_attr = AtributoFactory(nome="Cor", categoria=produto.categoria)
        cor_normal = ValorAtributoFactory(
            atributo=cor_attr,
            valor="Branco",
            preco_adicional=Decimal("0.00"),
            percentual_adicional=Decimal("0.00"),
        )

        variacao = VariacaoProdutoFactory(produto=produto, preco=Decimal("30.00"))
        variacao.valores.clear()
        variacao.valores.add(cor_normal)

        inline = VariacaoProdutoInline(produto.__class__, admin_site)
        preco_display = inline.preco_final_calculado(variacao)

        assert preco_display == "R$ 30,00"

    def test_admin_price_formatting(self, admin_site, admin_request):
        """Testa formatação de preços no admin"""
        produto = ProdutoFactory(produto="Produto Caro", preco=Decimal("1234.56"))

        # Atributo deve usar a mesma categoria do produto
        cor_attr = AtributoFactory(nome="Material", categoria=produto.categoria)
        cor_especial = ValorAtributoFactory(
            atributo=cor_attr,
            valor="Platina",
            preco_adicional=Decimal("500.44"),
            percentual_adicional=Decimal("0"),
        )

        variacao = VariacaoProdutoFactory(produto=produto, preco=Decimal("1234.56"))
        variacao.valores.clear()
        variacao.valores.add(cor_especial)

        inline = VariacaoProdutoInline(produto.__class__, admin_site)
        preco_display = inline.preco_final_calculado(variacao)

        # Verifica formatação brasileira
        assert preco_display == "R$ 1.735,00"  # 1234.56 + 500.44

    def test_valor_atributo_admin_search_functionality(self, admin_site, admin_request):
        """Testa funcionalidade de busca no admin"""
        admin_instance = ValorAtributoAdmin(ValorAtributo, admin_site)

        # Verifica campos de busca
        assert "valor" in admin_instance.search_fields
        assert "atributo__nome" in admin_instance.search_fields

        # Verifica filtros
        assert "atributo" in admin_instance.list_filter

    def test_atributo_admin_inline_fields(self, admin_site, admin_request):
        """Testa campos no inline do AtributoAdmin"""
        admin_instance = AtributoAdmin(Atributo, admin_site)

        # Verifica se tem inline
        assert len(admin_instance.inlines) > 0

        # Pega o inline
        valor_inline = admin_instance.inlines[0]
        inline_instance = valor_inline(Atributo, admin_site)

        # Verifica se os campos de preço estão incluídos
        if hasattr(inline_instance, "fields"):
            assert "preco_adicional" in inline_instance.fields
            assert "percentual_adicional" in inline_instance.fields
