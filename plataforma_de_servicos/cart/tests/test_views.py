import pytest
from django.urls import reverse
from django.test import Client
from decimal import Decimal

from plataforma_de_servicos.cart.cart import Cart
from plataforma_de_servicos.produto.tests.factories import VariacaoProdutoFactory

pytestmark = [pytest.mark.django_db, pytest.mark.cart]


@pytest.fixture
def variacao_factory(db):
    def factory(*args, **kwargs):
        return VariacaoProdutoFactory.create(*args, **kwargs)
    return factory


class TestCartViews:
    def test_cart_add_view(self, variacao_factory, client: Client):
        variacao = variacao_factory(preco=Decimal("25.00"))
        add_url = reverse("cart:cart-add")

        response = client.post(
            add_url,
            {
                "variation_id": variacao.id,
                "product_quantity": 2,
                "action": "post",
            },
            HTTP_HX_REQUEST="true",
        )

        # View retorna JSON para requisições HTMX, não um HX-Trigger direto
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True
        assert json_data["qty"] == 2
        assert "adicionado ao carrinho" in json_data["message"]

        cart = Cart(response.wsgi_request)
        assert len(cart) == 2
        assert str(variacao.id) in cart.cart

    def test_cart_delete_view(self, variacao_factory, client: Client):
        variacao = variacao_factory(preco=Decimal("50.00"))
        delete_url = reverse("cart:cart-delete")

        session = client.session
        session["cart"] = {
            str(variacao.id): {"preco": str(variacao.preco), "qty": 1}
        }
        session.save()

        response = client.post(
            delete_url,
            {"variation_id": variacao.id, "action": "post"},
            HTTP_HX_REQUEST="true",
        )

        assert response.status_code == 200
        json_response = response.json()
        assert Decimal(json_response["total"]) == Decimal("0.00")

        cart = Cart(response.wsgi_request)
        assert len(cart) == 0

    def test_cart_update_view(self, variacao_factory, client: Client):
        variacao = variacao_factory(preco=Decimal("30.00"))
        update_url = reverse("cart:cart-update")

        session = client.session
        session["cart"] = {
            str(variacao.id): {"preco": str(variacao.preco), "qty": 1}
        }
        session.save()

        response = client.post(
            update_url,
            {
                "variation_id": variacao.id,
                "product_quantity": 4,
                "action": "post",
            },
            HTTP_HX_REQUEST="true",
        )

        assert response.status_code == 200
        json_response = response.json()
        assert json_response["qty"] == 4
        assert Decimal(json_response["total"]) == Decimal("120.00")

        cart = Cart(response.wsgi_request)
        assert len(cart) == 4

    def test_cart_summary_view(self, variacao_factory, client: Client):
        variacao = variacao_factory()
        summary_url = reverse("cart:cart-summary")
        add_url = reverse("cart:cart-add")

        client.post(
            add_url,
            {"variation_id": variacao.id, "product_quantity": 1, "action": "post"},
            HTTP_HX_REQUEST="true",
        )

        response = client.get(summary_url)

        assert response.status_code == 200
        assert "pages/cart-summary.html" in (t.name for t in response.templates)
        # O contexto agora deve conter variações, não produtos
        assert any(v["variation"].id == variacao.id for v in response.context["cart"])