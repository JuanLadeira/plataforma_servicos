from decimal import Decimal
from unittest.mock import Mock

import pytest

from plataforma_de_servicos.produto.tests.factories import AtributoFactory
from plataforma_de_servicos.produto.tests.factories import ProdutoFactory
from plataforma_de_servicos.produto.tests.factories import ValorAtributoFactory
from plataforma_de_servicos.produto.tests.factories import VariacaoProdutoFactory

from ..cart import Cart

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.cart]


class TestCartPricing:
    """Testes para funcionalidade de preços no carrinho"""

    @pytest.fixture(scope="function")
    def request_mock(self):
        """Cria um mock de request com sessão"""
        request = Mock()
        request.session = Mock()
        request.session.session_key = "test_session_key"
        request.session.create = Mock()
        request.session.get = Mock(return_value={})
        request.session.__getitem__ = Mock(return_value={})
        request.session.__setitem__ = Mock()
        return request

    @pytest.fixture(scope="function")
    def cart(self, request_mock):
        """Cria uma instância do carrinho"""
        return Cart(request_mock)

    @pytest.fixture(scope="function")
    def base_data(self, django_db_setup, django_db_blocker):
        """Cria dados base reutilizáveis para otimizar performance"""
        with django_db_blocker.unblock():
            # Atributos base
            cor_attr = AtributoFactory(nome="Cor")
            tam_attr = AtributoFactory(nome="Tamanho")
            
            # Produtos base
            produto_base = ProdutoFactory(produto="BaseProduct", preco=Decimal("100.00"))
            produto_simples = ProdutoFactory(produto="SimpleProduct", preco=Decimal("50.00"))
            
            return {
                'cor_attr': cor_attr,
                'tam_attr': tam_attr,
                'produto_base': produto_base,
                'produto_simples': produto_simples
            }

    def test_add_variation_with_price_modifiers(self, cart, base_data):
        """Testa adição de variação com modificadores de preço"""
        # Usa dados base reutilizáveis
        produto = base_data['produto_base']
        cor_attr = base_data['cor_attr']

        # Cria valor com modificadores (mínimo necessário)
        valor_cor = ValorAtributoFactory.build(
            atributo=cor_attr,
            valor="Premium",
            preco_adicional=Decimal("20.00"),
            percentual_adicional=Decimal("10.00"),
        )
        valor_cor.save()

        # Cria variação com dados mínimos
        variacao = VariacaoProdutoFactory(produto=produto, preco=Decimal("100.00"))
        variacao.valores.set([valor_cor])  # Usa set() em vez de clear()+add()

        # Adiciona ao carrinho
        cart.add(variacao, 2)

        # Verifica cálculos
        cart_items = list(cart)
        assert len(cart_items) == 1
        assert cart_items[0]["preco"] == Decimal("130.00")
        assert cart_items[0]["qty"] == 2
        assert cart_items[0]["total"] == Decimal("260.00")

    def test_add_variation_multiple_times(self, cart, base_data):
        """Testa adição múltipla da mesma variação"""
        produto = base_data['produto_simples']
        cor_attr = base_data['cor_attr']

        # Valor sem modificadores (build otimizado)
        valor_cor = ValorAtributoFactory.build(
            atributo=cor_attr,
            valor="Normal",
            preco_adicional=Decimal("0"),
            percentual_adicional=Decimal("0"),
        )
        valor_cor.save()

        variacao = VariacaoProdutoFactory(produto=produto, preco=Decimal("50.00"))
        variacao.valores.set([valor_cor])

        # Adições múltiplas
        cart.add(variacao, 1)
        cart.add(variacao, 2)

        cart_items = list(cart)
        assert len(cart_items) == 1
        assert cart_items[0]["qty"] == 3
        assert cart_items[0]["preco"] == Decimal("50.00")

    def test_cart_iteration_recalculates_prices(self, cart, base_data):
        """Testa que o carrinho recalcula preços durante iteração"""
        produto = base_data['produto_base']
        cor_attr = base_data['cor_attr']

        # Valor com modificadores iniciais
        valor_cor = ValorAtributoFactory.build(
            atributo=cor_attr,
            valor="Premium",
            preco_adicional=Decimal("10.00"),
            percentual_adicional=Decimal("5.00"),
        )
        valor_cor.save()

        variacao = VariacaoProdutoFactory(produto=produto, preco=Decimal("100.00"))
        variacao.valores.set([valor_cor])

        cart.add(variacao, 1)

        # Simula mudança nos modificadores
        valor_cor.preco_adicional = Decimal("15.00")
        valor_cor.percentual_adicional = Decimal("8.00")
        valor_cor.save()

        # Verifica recálculo
        cart_items = list(cart)
        assert cart_items[0]["preco"] == Decimal("123.00")

    def test_cart_total_calculation(self, cart, base_data):
        """Testa cálculo do total do carrinho"""
        produto1 = base_data['produto_base']
        cor_attr = base_data['cor_attr']

        # Produto 2 adicional apenas para este teste
        produto2 = ProdutoFactory(produto="Produto2", preco=Decimal("200.00"))

        # Valores com build otimizado
        valor_premium = ValorAtributoFactory.build(
            atributo=cor_attr,
            valor="Premium",
            preco_adicional=Decimal("25.00"),
            percentual_adicional=Decimal("0"),
        )
        valor_premium.save()

        valor_normal = ValorAtributoFactory.build(
            atributo=cor_attr,
            valor="Normal",
            preco_adicional=Decimal("0"),
            percentual_adicional=Decimal("0"),
        )
        valor_normal.save()

        # Variações otimizadas
        variacao1 = VariacaoProdutoFactory(produto=produto1, preco=Decimal("100.00"))
        variacao1.valores.set([valor_premium])

        variacao2 = VariacaoProdutoFactory(produto=produto2, preco=Decimal("200.00"))
        variacao2.valores.set([valor_normal])

        # Teste de total
        cart.add(variacao1, 1)  # 125.00
        cart.add(variacao2, 2)  # 400.00

        total = cart.get_total()
        assert total == Decimal("525.00")

    def test_add_product_simple(self, cart, base_data):
        """Testa adição de produto simples (sem variação)"""
        produto = ProdutoFactory(produto="Produto Simples", preco=Decimal("80.00"))

        cart.add_product(produto, 3)

        cart_items = list(cart)
        assert len(cart_items) == 1
        assert cart_items[0]["preco"] == Decimal("80.00")
        assert cart_items[0]["qty"] == 3
        assert cart_items[0]["total"] == Decimal("240.00")

    def test_cart_length(self, cart, base_data):
        """Testa cálculo do comprimento do carrinho"""
        produto = base_data['produto_simples']
        cor_attr = base_data['cor_attr']

        # Valor otimizado
        valor_cor = ValorAtributoFactory.build(
            atributo=cor_attr,
            valor="Normal",
            preco_adicional=Decimal("0"),
            percentual_adicional=Decimal("0"),
        )
        valor_cor.save()

        variacao = VariacaoProdutoFactory(produto=produto, preco=Decimal("50.00"))
        variacao.valores.set([valor_cor])

        assert len(cart) == 0
        cart.add(variacao, 2)
        assert len(cart) == 2
        cart.add(variacao, 3)
        assert len(cart) == 5

    def test_multiple_attributes_pricing(self, cart, base_data):
        """Testa pricing com múltiplos atributos"""
        produto = ProdutoFactory(produto="Camiseta", preco=Decimal("50.00"))
        cor_attr = base_data['cor_attr']
        tam_attr = base_data['tam_attr']

        # Valores otimizados com build
        cor_especial = ValorAtributoFactory.build(
            atributo=cor_attr,
            valor="Dourado",
            preco_adicional=Decimal("15.00"),
            percentual_adicional=Decimal("0"),
        )
        cor_especial.save()

        tam_gg = ValorAtributoFactory.build(
            atributo=tam_attr,
            valor="GG",
            preco_adicional=Decimal("0"),
            percentual_adicional=Decimal("20.00"),
        )
        tam_gg.save()

        variacao = VariacaoProdutoFactory(produto=produto, preco=Decimal("50.00"))
        variacao.valores.set([cor_especial, tam_gg])

        cart.add(variacao, 1)

        cart_items = list(cart)
        # 50 + 15 + (50 * 0.20) = 75.00
        assert cart_items[0]["preco"] == Decimal("75.00")
