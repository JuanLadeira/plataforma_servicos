from decimal import Decimal

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory

from plataforma_de_servicos.produto.tests.factories import (
    AtributoFactory,
    ProdutoFactory,
    ValorAtributoFactory,
    VariacaoProdutoFactory,
)

from ..cart import Cart

pytestmark = [pytest.mark.django_db, pytest.mark.cart]


@pytest.fixture
def cart_request():
    """Cria um request com sessão real para o carrinho"""
    factory = RequestFactory()
    request = factory.get("/")
    request.session = SessionStore()
    request.session.create()
    return request


@pytest.fixture
def cart(cart_request):
    """Cria uma instância do carrinho"""
    return Cart(cart_request)


class TestCartPricing:
    """Testes para funcionalidade de preços no carrinho"""

    def test_add_variation_with_price_modifiers(self, cart):
        """Testa adição de variação com modificadores de preço"""
        cor_attr = AtributoFactory(nome="Cor Premium")
        valor_cor = ValorAtributoFactory(
            atributo=cor_attr,
            valor="Premium",
            preco_adicional=Decimal("20.00"),
            percentual_adicional=Decimal("10.00"),
        )

        variacao = VariacaoProdutoFactory(
            preco=Decimal("100.00"),
            valores=[valor_cor],
        )

        cart.add(variacao, 2)

        cart_items = list(cart)
        assert len(cart_items) == 1
        # Preço: 100 + 20 (adicional) + 10% de 100 (10) = 130
        assert cart_items[0]["preco"] == Decimal("130.00")
        assert cart_items[0]["qty"] == 2
        assert cart_items[0]["total"] == Decimal("260.00")

    def test_add_variation_multiple_times(self, cart):
        """Testa adição múltipla da mesma variação"""
        variacao = VariacaoProdutoFactory(preco=Decimal("50.00"))

        cart.add(variacao, 1)
        cart.add(variacao, 2)

        cart_items = list(cart)
        assert len(cart_items) == 1
        assert cart_items[0]["qty"] == 3
        assert cart_items[0]["preco"] == Decimal("50.00")

    def test_cart_iteration_recalculates_prices(self, cart_request):
        """Testa que o carrinho recalcula preços durante iteração"""
        cor_attr = AtributoFactory(nome="Cor Recalculo")
        valor_cor = ValorAtributoFactory(
            atributo=cor_attr,
            valor="Premium",
            preco_adicional=Decimal("10.00"),
            percentual_adicional=Decimal("5.00"),
        )

        variacao = VariacaoProdutoFactory(
            preco=Decimal("100.00"),
            valores=[valor_cor],
        )

        cart = Cart(cart_request)
        cart.add(variacao, 1)

        # Modifica os modificadores no banco
        valor_cor.preco_adicional = Decimal("15.00")
        valor_cor.percentual_adicional = Decimal("8.00")
        valor_cor.save()

        # Cria novo cart com mesma sessão para simular próxima requisição
        cart2 = Cart(cart_request)
        cart_items = list(cart2)
        # Preço: 100 + 15 + 8% de 100 (8) = 123
        assert cart_items[0]["preco"] == Decimal("123.00")

    def test_cart_total_calculation(self, cart):
        """Testa cálculo do total do carrinho"""
        cor_attr = AtributoFactory(nome="Cor Total")

        valor_premium = ValorAtributoFactory(
            atributo=cor_attr,
            valor="Premium Total",
            preco_adicional=Decimal("25.00"),
            percentual_adicional=Decimal("0"),
        )

        valor_normal = ValorAtributoFactory(
            atributo=cor_attr,
            valor="Normal Total",
            preco_adicional=Decimal("0"),
            percentual_adicional=Decimal("0"),
        )

        variacao1 = VariacaoProdutoFactory(
            preco=Decimal("100.00"),
            valores=[valor_premium],
        )
        variacao2 = VariacaoProdutoFactory(
            preco=Decimal("200.00"),
            valores=[valor_normal],
        )

        cart.add(variacao1, 1)  # 125.00
        cart.add(variacao2, 2)  # 400.00

        total = cart.get_total()
        assert total == Decimal("525.00")

    def test_add_product_simple(self, cart):
        """Testa adição de produto simples (sem variação)"""
        produto = ProdutoFactory(
            produto="Produto Simples",
            preco=Decimal("80.00"),
            estoque=10,
        )

        cart.add_product(produto, 3)

        cart_items = list(cart)
        assert len(cart_items) == 1
        assert cart_items[0]["preco"] == Decimal("80.00")
        assert cart_items[0]["qty"] == 3
        assert cart_items[0]["total"] == Decimal("240.00")

    def test_cart_length(self, cart):
        """Testa cálculo do comprimento do carrinho"""
        variacao = VariacaoProdutoFactory(preco=Decimal("50.00"))

        assert len(cart) == 0
        cart.add(variacao, 2)
        assert len(cart) == 2
        cart.add(variacao, 3)
        assert len(cart) == 5

    def test_multiple_attributes_pricing(self, cart):
        """Testa pricing com múltiplos atributos"""
        cor_attr = AtributoFactory(nome="Cor Multi")
        tam_attr = AtributoFactory(nome="Tamanho Multi")

        cor_especial = ValorAtributoFactory(
            atributo=cor_attr,
            valor="Dourado",
            preco_adicional=Decimal("15.00"),
            percentual_adicional=Decimal("0"),
        )

        tam_gg = ValorAtributoFactory(
            atributo=tam_attr,
            valor="GG",
            preco_adicional=Decimal("0"),
            percentual_adicional=Decimal("20.00"),
        )

        variacao = VariacaoProdutoFactory(
            preco=Decimal("50.00"),
            valores=[cor_especial, tam_gg],
        )

        cart.add(variacao, 1)

        cart_items = list(cart)
        # 50 + 15 + (50 * 0.20) = 75.00
        assert cart_items[0]["preco"] == Decimal("75.00")
