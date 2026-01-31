import json
from decimal import Decimal
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client
from django.test import RequestFactory
from django.test import TestCase

from plataforma_de_servicos.cart.cart import Cart
from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.estoque.choices.origem_saida import OrigemSaida
from plataforma_de_servicos.estoque.models import Estoque
from plataforma_de_servicos.estoque.models import EstoqueItens
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.payment.models import Order
from plataforma_de_servicos.payment.models import OrderItem
from plataforma_de_servicos.payment.views import complete_order
from plataforma_de_servicos.produto.models import Categoria
from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.produto.models import VariacaoProduto

pytestmark = [
    pytest.mark.payment,
    pytest.mark.integration,
    pytest.mark.skip(reason="OBSOLETO: Módulo de payment não está mais em uso. Fluxo de vendas migrado para OrdemCompra."),
]

User = get_user_model()


class PaymentEstoqueIntegrationTest(TestCase):
    """
    OBSOLETO: Estes testes são do módulo de payment legado.
    O fluxo de vendas foi migrado para usar OrdemCompra e o campo
    pedido_id foi substituído por ordem_compra (ForeignKey).
    """
    def setUp(self):
        """Configurar dados de teste"""
        self.factory = RequestFactory()
        self.client = Client()

        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )

        self.inventario = Inventario.objects.create(
            nome="Estoque Principal",
        )

        self.categoria = Categoria.objects.create(categoria="Eletrônicos")

        self.produto1 = Produto.objects.create(
            produto="Laptop",
            preco=Decimal("2000.00"),
            estoque=10,
            categoria=self.categoria,
        )

        self.produto2 = Produto.objects.create(
            produto="Teclado",
            preco=Decimal("150.00"),
            estoque=25,
            categoria=self.categoria,
        )

        self.variacao = VariacaoProduto.objects.create(
            produto=self.produto1,
            sku="LAP001",
            preco=Decimal("2100.00"),
            estoque=5,
        )

    def create_request_with_session_and_cart(self):
        """Criar request com sessão e carrinho configurados"""
        request = self.factory.post("/payment/complete-order/")
        middleware = SessionMiddleware(MagicMock())
        middleware.process_request(request)
        request.session.save()

        # Adicionar itens ao carrinho
        cart = Cart(request)
        cart.add_product(self.produto1, 2)
        cart.add(self.variacao, 1)
        cart.add_product(self.produto2, 3)

        return request, cart

    def test_complete_order_cria_saida_estoque(self):
        """Testar que finalizar pedido cria saída de estoque"""
        request, cart = self.create_request_with_session_and_cart()
        request.user = self.user

        # Simular dados do formulário
        request.POST = {
            "action": "post",
            "name": "João Silva",
            "email": "joao@example.com",
            "address1": "Rua A, 123",
            "address2": "Apt 45",
            "city": "São Paulo",
            "state": "SP",
            "zipcode": "01234-567",
        }

        estoque_inicial_p1 = self.produto1.estoque
        estoque_inicial_p2 = self.produto2.estoque

        response = complete_order(request)

        # Verificar resposta de sucesso
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data["success"])

        # Verificar que pedido foi criado
        order = Order.objects.get(id=response_data["order_id"])
        self.assertEqual(order.full_name, "João Silva")
        self.assertEqual(order.user, self.user)

        # Verificar que itens do pedido foram criados
        order_items = OrderItem.objects.filter(order=order)
        self.assertEqual(order_items.count(), 3)

        # Verificar saída de estoque (agora usa criar_saida_manual, sem ordem_compra)
        saida_estoque = Estoque.objects.filter(
            movimento=Movimento.SAIDA.value,
            origem_saida=OrigemSaida.PEDIDO.value,
            observacao__contains=f"Order #{order.id}",
        ).first()

        self.assertIsNotNone(saida_estoque)
        self.assertEqual(saida_estoque.funcionario, self.user)
        # Saída manual não é processada automaticamente
        self.assertTrue(saida_estoque.processado)

        # Verificar itens da saída de estoque
        itens_saida = EstoqueItens.objects.filter(estoque=saida_estoque)
        self.assertEqual(itens_saida.count(), 3)

        # Verificar quantidades
        item_p1 = itens_saida.filter(produto=self.produto1, quantidade=2).first()
        item_p1_var = itens_saida.filter(produto=self.produto1, quantidade=1).first()
        item_p2 = itens_saida.filter(produto=self.produto2, quantidade=3).first()

        self.assertIsNotNone(item_p1)
        self.assertIsNotNone(item_p1_var)
        self.assertIsNotNone(item_p2)

        # Verificar que estoque foi atualizado
        self.produto1.refresh_from_db()
        self.produto2.refresh_from_db()
        self.assertEqual(self.produto1.estoque, estoque_inicial_p1 - 3)  # 2 + 1
        self.assertEqual(self.produto2.estoque, estoque_inicial_p2 - 3)


    def test_complete_order_guest_user(self):
        """Testar finalização de pedido com usuário não autenticado"""
        request, cart = self.create_request_with_session_and_cart()
        request.user = MagicMock()
        request.user.is_authenticated = False

        request.POST = {
            "action": "post",
            "name": "Guest User",
            "email": "guest@example.com",
            "address1": "Guest Address",
            "address2": "",
            "city": "Guest City",
            "state": "GS",
            "zipcode": "54321",
        }

        response = complete_order(request)
        response_data = json.loads(response.content)

        # Verificar que pedido foi criado sem usuário
        order = Order.objects.get(id=response_data["order_id"])
        self.assertIsNone(order.user)
        self.assertEqual(order.full_name, "Guest User")

        # Verificar que saída de estoque foi criada sem funcionário
        saida = Estoque.objects.filter(observacao__contains=f"Order #{order.id}").first()
        self.assertIsNotNone(saida)
        self.assertIsNone(saida.funcionario)

    def test_complete_order_erro_estoque_nao_quebra_pedido(self):
        """Testar que erro no estoque não quebra criação do pedido"""
        request, cart = self.create_request_with_session_and_cart()
        request.user = self.user

        request.POST = {
            "action": "post",
            "name": "Test User",
            "email": "test@example.com",
            "address1": "Test Address",
            "address2": "",
            "city": "Test City",
            "state": "TS",
            "zipcode": "12345",
        }

        # Mock que simula erro na criação da saída de estoque
        with patch("plataforma_de_servicos.estoque.services.EstoqueService.criar_saida_manual") as mock_service:
            mock_service.side_effect = Exception("Erro no estoque")

            response = complete_order(request)
            response_data = json.loads(response.content)

            # Pedido deve ser criado mesmo com erro no estoque
            self.assertTrue(response_data["success"])
            order = Order.objects.get(id=response_data["order_id"])
            self.assertIsNotNone(order)

    def test_complete_order_transacao_atomica(self):
        """Testar que erro geral reverte toda a transação"""
        request, cart = self.create_request_with_session_and_cart()
        request.user = self.user

        request.POST = {
            "action": "post",
            "name": "Test User",
            "email": "test@example.com",
            "address1": "Test Address",
            "address2": "",
            "city": "Test City",
            "state": "TS",
            "zipcode": "12345",
        }

        # Mock que simula erro na criação do pedido
        with patch("plataforma_de_servicos.payment.models.Order.objects.create") as mock_create:
            mock_create.side_effect = Exception("Erro na criação do pedido")

            response = complete_order(request)

            # Deve retornar erro
            self.assertEqual(response.status_code, 400)
            response_data = json.loads(response.content)
            self.assertFalse(response_data["success"])

            # Nenhum pedido deve ter sido criado
            self.assertEqual(Order.objects.count(), 0)
            self.assertEqual(OrderItem.objects.count(), 0)

    def test_order_items_com_variacoes(self):
        """Testar que OrderItems são criados corretamente com variações"""
        request, cart = self.create_request_with_session_and_cart()
        request.user = self.user

        request.POST = {
            "action": "post",
            "name": "Test User",
            "email": "test@example.com",
            "address1": "Test Address",
            "address2": "",
            "city": "Test City",
            "state": "TS",
            "zipcode": "12345",
        }

        response = complete_order(request)
        response_data = json.loads(response.content)
        order = Order.objects.get(id=response_data["order_id"])

        # Verificar itens do pedido
        order_items = OrderItem.objects.filter(order=order)

        # Item com variação
        item_variacao = order_items.filter(variacao_produto=self.variacao).first()
        self.assertIsNotNone(item_variacao)
        self.assertEqual(item_variacao.produto, self.produto1)
        self.assertEqual(item_variacao.quantity, 1)

        # Itens sem variação
        itens_simples = order_items.filter(variacao_produto__isnull=True)
        self.assertEqual(itens_simples.count(), 2)

    def test_payment_service_clear_reservations(self):
        """Testar que PaymentService.clear_cart_reservations funciona corretamente"""
        # Teste desativado pois a lógica de ReservaEstoque foi removida.
        pass

    def test_payment_success_limpa_reservas_fallback(self):
        """Testar que payment_success limpa reservas como fallback"""
        # Teste desativado pois a lógica de ReservaEstoque foi removida.
        pass
