import json
from decimal import Decimal
from unittest.mock import MagicMock
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client
from django.test import RequestFactory
from django.test import TestCase

from plataforma_de_servicos.cart.cart import Cart
from plataforma_de_servicos.cart.models import ReservaEstoque
from plataforma_de_servicos.cart.views import cart_add
from plataforma_de_servicos.produto.models import Categoria
from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.produto.models import VariacaoProduto

User = get_user_model()


class CartViewsTest(TestCase):
    def setUp(self):
        """Configurar dados de teste"""
        self.factory = RequestFactory()
        self.client = Client()
        
        # Limpar reservas de testes anteriores que podem ter vazado de threads
        from plataforma_de_servicos.cart.models import ReservaEstoque
        ReservaEstoque.objects.all().delete()

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

        # Session middleware
        if session:
            request.session = session
        else:
            session_middleware = SessionMiddleware(MagicMock())
            session_middleware.process_request(request)
            request.session.save()

        # Messages middleware
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
        request.META["HTTP_HX_REQUEST"] = "true"  # Simular requisição HTMX

        response = cart_add(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn("qty", response_data)
        self.assertIn("redirect", response_data)
        self.assertEqual(response_data["qty"], 2)

        # Verificar que reserva foi criada
        self.assertEqual(ReservaEstoque.objects.count(), 1)
        reserva = ReservaEstoque.objects.first()
        self.assertEqual(reserva.produto, self.produto)
        self.assertEqual(reserva.quantidade, 2)

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
        self.assertEqual(response_data["qty"], 1)

        # Verificar que reserva foi criada para variação
        reserva = ReservaEstoque.objects.first()
        self.assertEqual(reserva.variacao_produto, self.variacao)

    def test_cart_add_estoque_insuficiente(self):
        """Testar tentativa de adicionar mais produtos que o disponível"""
        data = {
            "action": "post",
            "product_id": str(self.produto.id),
            "product_quantity": str(self.produto.estoque + 5),  # Mais que o disponível
        }

        request = self.create_request_with_middleware(data=data)
        request.META["HTTP_HX_REQUEST"] = "true"

        response = cart_add(request)

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn("error", response_data)
        self.assertIn("redirect", response_data)

        # Nenhuma reserva deve ter sido criada
        self.assertEqual(ReservaEstoque.objects.count(), 0)

    def test_cart_add_produto_ja_no_carrinho_sem_estoque(self):
        """Testar adicionar produto que já está no carrinho e não há mais estoque"""
        # Adicionar produto ao carrinho primeiro
        cart = Cart(self.create_request_with_middleware())
        cart.add_product(self.produto, self.produto.estoque)  # Esgotar estoque

        # Tentar adicionar mais
        data = {
            "action": "post",
            "product_id": str(self.produto.id),
            "product_quantity": "1",
        }

        request = self.create_request_with_middleware(data=data)
        request.META["HTTP_HX_REQUEST"] = "true"

        response = cart_add(request)
        response_data = json.loads(response.content)

        self.assertIn("error", response_data)

    def test_cart_add_considera_reservas_outros_usuarios(self):
        """Testar que validação considera reservas de outros usuários"""
        # Criar reserva de outro usuário
        ReservaEstoque.objects.create(
            session_key="outra_sessao_123",
            produto=self.produto,
            quantidade=8,  # Reservar quase todo o estoque
        )

        # Tentar adicionar produto
        data = {
            "action": "post",
            "product_id": str(self.produto.id),
            "product_quantity": "5",  # Mais que o disponível
        }

        request = self.create_request_with_middleware(data=data)
        request.META["HTTP_HX_REQUEST"] = "true"

        response = cart_add(request)
        response_data = json.loads(response.content)

        # Deve dar erro de estoque insuficiente
        self.assertIn("error", response_data)

    def test_cart_add_nao_considera_propria_reserva(self):
        """Testar que não considera sua própria reserva como indisponível"""
        # Primeira requisição para criar reserva
        data_initial = {
            "action": "post",
            "product_id": str(self.produto.id),
            "product_quantity": "3",
        }
        request = self.create_request_with_middleware(data=data_initial)
        request.META["HTTP_HX_REQUEST"] = "true"
        
        # Adicionar produto pela primeira vez
        cart_add(request)
        
        # Salvar sessão para usar na segunda requisição
        session = request.session

        # Tentar adicionar mais do mesmo produto usando a mesma sessão
        data = {
            "action": "post",
            "product_id": str(self.produto.id),
            "product_quantity": "2",  # Total ficará 5
        }

        request2 = self.create_request_with_middleware(data=data, session=session)
        request2.META["HTTP_HX_REQUEST"] = "true"

        response = cart_add(request2)
        response_data = json.loads(response.content)

        # Deve funcionar pois é nossa própria reserva
        self.assertNotIn("error", response_data)
        self.assertEqual(response_data["qty"], 5)

    def test_cart_add_sem_action_post(self):
        """Testar requisição sem action=post"""
        request = self.create_request_with_middleware()

        response = cart_add(request)

        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn("error", response_data)

    def test_cart_add_produto_inexistente(self):
        """Testar adicionar produto que não existe"""
        data = {
            "action": "post",
            "product_id": "99999",  # ID inexistente
            "product_quantity": "1",
        }

        request = self.create_request_with_middleware(data=data)

        # Deve retornar 404
        with self.assertRaises(Exception):  # get_object_or_404 levanta exceção
            cart_add(request)

    def test_cart_add_sem_htmx_redireciona_diretamente(self):
        """Testar que sem HTMX retorna redirect direto"""
        data = {
            "action": "post",
            "product_id": str(self.produto.id),
            "product_quantity": "1",
        }

        request = self.create_request_with_middleware(data=data)
        # Sem definir HTTP_HX_REQUEST

        response = cart_add(request)

        # Deve ser redirect
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/cart/")

    def test_cart_add_quantidade_zero(self):
        """Testar adicionar quantidade zero"""
        data = {
            "action": "post",
            "product_id": str(self.produto.id),
            "product_quantity": "0",
        }

        request = self.create_request_with_middleware(data=data)

        # Deve aceitar mas não adicionar nada
        response = cart_add(request)
        self.assertEqual(response.status_code, 302)

    def test_cart_add_quantidade_negativa(self):
        """Testar adicionar quantidade negativa"""
        data = {
            "action": "post",
            "product_id": str(self.produto.id),
            "product_quantity": "-1",
        }

        request = self.create_request_with_middleware(data=data)

        # Deve tratar como valor absoluto ou dar erro
        with self.assertRaises(ValueError):
            cart_add(request)

    @patch("plataforma_de_servicos.cart.models.ReservaEstoque.get_quantidade_reservada")
    def test_cart_add_erro_calculo_reservas(self, mock_get_quantidade):
        """Testar comportamento quando há erro no cálculo de reservas"""
        mock_get_quantidade.side_effect = Exception("Erro no banco")

        data = {
            "action": "post",
            "product_id": str(self.produto.id),
            "product_quantity": "1",
        }

        request = self.create_request_with_middleware(data=data)

        # Deve funcionar mesmo com erro nas reservas (fallback)
        response = cart_add(request)
        self.assertEqual(response.status_code, 302)

    def test_cart_add_mensagens_corretas(self):
        """Testar que mensagens corretas são adicionadas"""
        # Teste de sucesso
        data = {
            "action": "post",
            "product_id": str(self.produto.id),
            "product_quantity": "1",
        }

        request = self.create_request_with_middleware(data=data)
        cart_add(request)

        # Verificar mensagens (seria necessário acessar request._messages)
        messages = list(request._messages)
        self.assertTrue(any("adicionado ao carrinho" in str(m) for m in messages))

    def test_cart_add_estoque_limite_exato(self):
        """Testar adição quando quantidade solicitada é exatamente o estoque"""
        data = {
            "action": "post",
            "product_id": str(self.produto.id),
            "product_quantity": str(self.produto.estoque),  # Exatamente o estoque disponível
        }

        request = self.create_request_with_middleware(data=data)
        request.META["HTTP_HX_REQUEST"] = "true"

        response = cart_add(request)
        response_data = json.loads(response.content)

        # Deve funcionar
        self.assertNotIn("error", response_data)
        self.assertEqual(response_data["qty"], self.produto.estoque)
