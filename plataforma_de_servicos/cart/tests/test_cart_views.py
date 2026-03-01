import json
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client
from django.test import RequestFactory
from django.test import TestCase

from plataforma_de_servicos.cart.cart import Cart
from plataforma_de_servicos.cart.views import cart_add
from plataforma_de_servicos.produto.models import Categoria
from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.produto.models import VariacaoProduto

pytestmark = pytest.mark.cart

User = get_user_model()


class CartViewsTest(TestCase):
    def setUp(self):
        """Configurar dados de teste"""
        self.factory = RequestFactory()
        self.client = Client()

        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )

        self.categoria = Categoria.objects.create(categoria="Eletrônicos")

        self.produto = Produto.objects.create(
            produto="Tablet",
            preco=Decimal("600.00"),
            estoque=10,
            categoria=self.categoria,
            ncm="12345678",
        )

        self.variacao = VariacaoProduto.objects.create(
            produto=self.produto,
            sku="TAB001",
            preco=Decimal("650.00"),
            estoque=5,
        )

    def create_request_with_middleware(self, method="POST", data=None, session=None):
        """Criar request com todos os middlewares necessários"""
        if method == "POST":
            request = self.factory.post("/cart/add/", data or {})
        else:
            request = self.factory.get("/cart/add/")

        if session:
            request.session = session
        else:
            session_middleware = SessionMiddleware(MagicMock())
            session_middleware.process_request(request)
            request.session.save()

        request._messages = FallbackStorage(request)
        request.user = self.user
        return request

    def test_cart_add_produto_simples_sucesso(self):
        """Testar adição de produto simples com sucesso"""
        data = {
            "action": "post",
            "product_id": str(self.produto.id),
            "product_quantity": "2",
        }
        request = self.create_request_with_middleware(data=data)
        request.META["HTTP_HX_REQUEST"] = "true"

        response = cart_add(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data.get("success"))
        self.assertIn("redirect", response_data)
        self.assertIn("message", response_data)
        self.assertEqual(response_data["qty"], 2)

        cart = Cart(request)
        self.assertEqual(len(cart), 2)

    def test_cart_add_variacao_sucesso(self):
        """Testar adição de variação de produto com sucesso"""
        data = {
            "action": "post",
            "variation_id": str(self.variacao.id),
            "product_quantity": "1",
        }
        request = self.create_request_with_middleware(data=data)
        request.META["HTTP_HX_REQUEST"] = "true"

        response = cart_add(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data.get("success"))
        self.assertIn("redirect", response_data)

        cart = Cart(request)
        self.assertEqual(len(cart), 1)

    def test_cart_add_estoque_insuficiente(self):
        """Testar tentativa de adicionar mais produtos que o estoque físico"""
        data = {
            "action": "post",
            "product_id": str(self.produto.id),
            "product_quantity": str(self.produto.estoque + 1),
        }
        request = self.create_request_with_middleware(data=data)
        request.META["HTTP_HX_REQUEST"] = "true"

        response = cart_add(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data.get("error"))
        self.assertIn("message", response_data)

        cart = Cart(request)
        self.assertEqual(len(cart), 0)

    def test_cart_add_produto_ja_no_carrinho_sem_estoque(self):
        """Testar adicionar produto que já está no carrinho e não há mais estoque"""
        request_initial = self.create_request_with_middleware()
        cart = Cart(request_initial)
        cart.add_product(self.produto, self.produto.estoque)

        data = {
            "action": "post",
            "product_id": str(self.produto.id),
            "product_quantity": "1",
        }
        request_next = self.create_request_with_middleware(data=data, session=request_initial.session)
        request_next.META["HTTP_HX_REQUEST"] = "true"

        response = cart_add(request_next)
        response_data = json.loads(response.content)
        self.assertTrue(response_data.get("error"))
        self.assertIn("message", response_data)

    def test_cart_add_sem_action_post(self):
        """Testar requisição sem action=post"""
        request = self.create_request_with_middleware()
        response = cart_add(request)
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn("error", response_data)

    def test_cart_add_produto_inexistente(self):
        """Testar adicionar produto que não existe retorna erro"""
        data = {
            "action": "post",
            "product_id": "99999",
            "product_quantity": "1",
        }
        request = self.create_request_with_middleware(data=data)
        request.META["HTTP_HX_REQUEST"] = "true"
        response = cart_add(request)

        # CartService retorna erro em vez de levantar Http404
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data.get("error"))
        self.assertIn("message", response_data)
        self.assertIn("Produto não encontrado", response_data["message"])

    def test_cart_add_sem_htmx_redireciona_diretamente(self):
        """Testar que sem HTMX retorna redirect direto"""
        data = {
            "action": "post",
            "product_id": str(self.produto.id),
            "product_quantity": "1",
        }
        request = self.create_request_with_middleware(data=data)
        response = cart_add(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/cart/")

    def test_cart_add_quantidade_zero_ou_negativa(self):
        """Testar que adicionar quantidade zero ou negativa não altera o carrinho"""
        data = {
            "action": "post",
            "product_id": str(self.produto.id),
            "product_quantity": "0",
        }
        request = self.create_request_with_middleware(data=data)
        cart_add(request)
        cart = Cart(request)
        self.assertEqual(len(cart), 0)

        data["product_quantity"] = "-1"
        request_neg = self.create_request_with_middleware(data=data)
        cart_add(request_neg)
        cart = Cart(request_neg)
        self.assertEqual(len(cart), 0)

    def test_cart_add_estoque_limite_exato(self):
        """Testar adição quando quantidade solicitada é exatamente o estoque"""
        data = {
            "action": "post",
            "product_id": str(self.produto.id),
            "product_quantity": str(self.produto.estoque),
        }
        request = self.create_request_with_middleware(data=data)
        request.META["HTTP_HX_REQUEST"] = "true"

        response = cart_add(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data.get("success"))
        self.assertIn("redirect", response_data)
        cart = Cart(request)
        self.assertEqual(len(cart), self.produto.estoque)
