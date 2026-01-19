from decimal import Decimal

import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory

from plataforma_de_servicos.cart.cart import Cart
from plataforma_de_servicos.produto.tests.factories import VariacaoProdutoFactory


@pytest.fixture
def variacao_factory(db):
    def factory(*args, **kwargs):
        return VariacaoProdutoFactory.create(*args, **kwargs)
    return factory


@pytest.mark.django_db
class TestCart:
    def test_cart_add_variation(self, variacao_factory):
        variacao = variacao_factory(preco=Decimal("19.99"))

        factory = RequestFactory()
        request = factory.get("/")
        request.session = SessionStore()

        cart = Cart(request)
        cart.add(variation=variacao, product_qty=1)

        cart_item = cart.cart[str(variacao.id)]
        assert cart_item["qty"] == 1
        assert cart_item["preco"] == str(variacao.preco)
        assert len(cart) == 1

        cart.add(variation=variacao, product_qty=3)
        assert cart.cart[str(variacao.id)]["qty"] == 4  # 1 + 3 = 4
        assert len(cart) == 4  # total de itens no carrinho

    def test_cart_delete_variation(self, variacao_factory):
        variacao = variacao_factory()

        factory = RequestFactory()
        request = factory.get("/")
        request.session = SessionStore()
        request.session["cart"] = {
            str(variacao.id): {"preco": str(variacao.preco), "qty": 2},
        }
        request.session.save()

        cart = Cart(request)
        assert len(cart) == 2

        cart.delete(variation=variacao.id)
        assert str(variacao.id) not in cart.cart
        assert len(cart) == 0

    def test_cart_update_variation(self, variacao_factory):
        variacao = variacao_factory()

        factory = RequestFactory()
        request = factory.get("/")
        request.session = SessionStore()
        request.session["cart"] = {
            str(variacao.id): {"preco": str(variacao.preco), "qty": 1},
        }
        request.session.save()

        cart = Cart(request)
        assert cart.cart[str(variacao.id)]["qty"] == 1

        cart.update(variation=variacao.id, qty=5)
        assert cart.cart[str(variacao.id)]["qty"] == 5
        assert len(cart) == 5

    def test_get_total(self, variacao_factory):
        variacao1 = variacao_factory(preco=Decimal("15.50"))
        variacao2 = variacao_factory(preco=Decimal("10.00"))

        factory = RequestFactory()
        request = factory.get("/")
        request.session = SessionStore()
        request.session["cart"] = {
            str(variacao1.id): {"preco": str(variacao1.preco), "qty": 2},  # 31.00
            str(variacao2.id): {"preco": str(variacao2.preco), "qty": 3},  # 30.00
        }
        request.session.save()

        cart = Cart(request)
        assert cart.get_total() == Decimal("61.00")

    def test_cart_iteration(self, variacao_factory):
        variacao1 = variacao_factory(preco=Decimal("20.00"))
        variacao2 = variacao_factory(preco=Decimal("5.00"))

        factory = RequestFactory()
        request = factory.get("/")
        request.session = SessionStore()
        request.session["cart"] = {
            str(variacao1.id): {"preco": str(variacao1.preco), "qty": 1},
            str(variacao2.id): {"preco": str(variacao2.preco), "qty": 4},
        }
        request.session.save()

        cart = Cart(request)

        items_in_cart = list(cart)
        assert len(items_in_cart) == 2

        item1 = next(item for item in items_in_cart if item["variation"].id == variacao1.id)
        item2 = next(item for item in items_in_cart if item["variation"].id == variacao2.id)

        assert item1["total"] == Decimal("20.00")
        assert item2["total"] == Decimal("20.00")
        assert item1["qty"] == 1
        assert item2["qty"] == 4
        assert item1["variation"].produto == variacao1.produto
