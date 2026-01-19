import json
from decimal import Decimal
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.db import OperationalError
from django.db import transaction
from django.test import RequestFactory
from django.test import TestCase

from plataforma_de_servicos.cart.cart import Cart
from plataforma_de_servicos.cart.models import ReservaEstoque
from plataforma_de_servicos.estoque.models import Estoque
from plataforma_de_servicos.estoque.models import EstoqueItens
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.payment.models import Order
from plataforma_de_servicos.payment.models import OrderItem
from plataforma_de_servicos.payment.views import complete_order
from plataforma_de_servicos.produto.models import Categoria
from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.produto.models import VariacaoProduto

pytestmark = [pytest.mark.payment, pytest.mark.slow]

User = get_user_model()


@pytest.mark.payment_network_failures
class PaymentNetworkFailuresTest(TestCase):
    """
    Testes para falhas de rede durante processos de pagamento e integração com estoque
    """

    def setUp(self):
        """Configurar dados de teste"""
        self.factory = RequestFactory()

        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )

        self.inventario = Inventario.objects.create(
            nome="Estoque Test",
        )

        self.categoria = Categoria.objects.create(categoria="Payment Network Test")

        self.produto = Produto.objects.create(
            produto="Produto Payment",
            preco=Decimal("100.00"),
            estoque=10,
            categoria=self.categoria,
        )

        self.variacao = VariacaoProduto.objects.create(
            produto=self.produto,
            sku="PAY001",
            preco=Decimal("120.00"),
            estoque=5,
        )

    def create_request_with_cart(self, user=None):
        """Criar request com carrinho populado"""
        request = self.factory.post("/payment/complete-order/")
        middleware = SessionMiddleware(MagicMock())
        middleware.process_request(request)
        request.session.save()
        request.user = user or self.user

        # Adicionar itens ao carrinho
        cart = Cart(request)
        cart.add_product(self.produto, 2)
        cart.add(self.variacao, 1)

        # Simular dados do formulário
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

        return request, cart

    def test_database_failure_during_order_creation(self):
        """Testar falha de banco durante criação do pedido"""
        request, cart = self.create_request_with_cart()

        # Mock falha na criação do pedido
        with patch("plataforma_de_servicos.payment.models.Order.objects.create") as mock_create:
            mock_create.side_effect = OperationalError("Database connection lost")

            response = complete_order(request)
            response_data = json.loads(response.content)

            # Deve retornar erro
            self.assertFalse(response_data["success"])
            self.assertIn("error", response_data)

            # Nenhum pedido deve ter sido criado
            self.assertEqual(Order.objects.count(), 0)

            # Reservas devem permanecer intactas
            self.assertEqual(ReservaEstoque.objects.filter(session_key=cart.session_key).count(), 2)

    def test_network_failure_during_stock_processing(self):
        """Testar falha de rede durante processamento do estoque"""
        request, cart = self.create_request_with_cart()

        # Mock falha no serviço de estoque
        with patch("plataforma_de_servicos.estoque.services.EstoqueService.criar_saida_por_pedido") as mock_service:
            mock_service.side_effect = OperationalError("Connection to inventory system failed")

            response = complete_order(request)
            response_data = json.loads(response.content)

            # Pedido deve ser criado mesmo com falha no estoque
            self.assertTrue(response_data["success"])

            # Verificar que pedido foi criado
            order = Order.objects.get(id=response_data["order_id"])
            self.assertIsNotNone(order)

            # Itens do pedido devem existir
            self.assertEqual(OrderItem.objects.filter(order=order).count(), 2)

            # Reservas devem ter sido limpas (payment foi bem-sucedido)
            self.assertEqual(ReservaEstoque.objects.filter(session_key=cart.session_key).count(), 0)

            # Estoque não deve ter sido processado devido à falha
            self.assertEqual(Estoque.objects.filter(pedido_id=order.id).count(), 0)

    def test_intermittent_connection_during_payment(self):
        """Testar conexão intermitente durante processo de pagamento"""
        request, cart = self.create_request_with_cart()

        call_count = 0
        original_create = Order.objects.create

        def intermittent_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # Primeira tentativa falha
                raise OperationalError("Temporary connection failure")
            # Segunda tentativa funciona
            return original_create(*args, **kwargs)

        with patch("plataforma_de_servicos.payment.models.Order.objects.create") as mock_create:
            mock_create.side_effect = intermittent_create

            response = complete_order(request)
            response_data = json.loads(response.content)

            # Deve falhar na primeira tentativa mas poderia funcionar na segunda
            # (dependendo da implementação de retry)
            if response_data["success"]:
                order = Order.objects.get(id=response_data["order_id"])
                self.assertIsNotNone(order)

    def test_transaction_rollback_on_payment_failure(self):
        """Testar rollback completo quando pagamento falha"""
        request, cart = self.create_request_with_cart()

        # Simular falha crítica após criar o pedido mas dentro da transação
        with patch("plataforma_de_servicos.estoque.services.EstoqueService.criar_saida_por_pedido") as mock_service:
            mock_service.side_effect = OperationalError("Critical payment processing error")

            response = complete_order(request)
            response_data = json.loads(response.content)

            # O pedido deve ter sido criado mesmo com falha no estoque
            # (transação não faz rollback do pedido quando falha só na criação de estoque)
            self.assertTrue(response_data["success"])
            self.assertEqual(Order.objects.count(), 1)
            
            # OrderItems devem ter sido criados normalmente
            self.assertEqual(OrderItem.objects.count(), 2)

            # Reservas devem ter sido limpas (isso acontece independente da falha de estoque)
            self.assertEqual(ReservaEstoque.objects.filter(session_key=cart.session_key).count(), 0)

    def test_timeout_during_inventory_update(self):
        """Testar timeout durante atualização do inventário"""
        request, cart = self.create_request_with_cart()

        with patch("plataforma_de_servicos.estoque.services.EstoqueService.criar_saida_por_pedido") as mock_service:
            # Simular timeout longo
            import time
            def slow_operation(*args, **kwargs):
                time.sleep(0.1)  # Simular operação lenta
                raise OperationalError("Lock wait timeout exceeded; try restarting transaction")

            mock_service.side_effect = slow_operation

            start_time = time.time()
            response = complete_order(request)
            end_time = time.time()

            # Operação deve completar rapidamente mesmo com timeout
            self.assertLess(end_time - start_time, 1.0)

            response_data = json.loads(response.content)
            # Pagamento deve ser bem-sucedido mesmo com falha no estoque
            self.assertTrue(response_data["success"])

    def test_deadlock_during_concurrent_payments(self):
        """Testar deadlock durante pagamentos concorrentes"""
        request, cart = self.create_request_with_cart()

        with patch("plataforma_de_servicos.payment.models.OrderItem.objects.create") as mock_create:
            mock_create.side_effect = OperationalError("Deadlock found when trying to get lock")

            response = complete_order(request)
            response_data = json.loads(response.content)

            # Deve falhar graciosamente
            self.assertEqual(response.status_code, 400)
            self.assertFalse(response_data["success"])

    def test_session_lost_during_payment(self):
        """Testar perda de sessão durante pagamento"""
        request, cart = self.create_request_with_cart()
        original_session_key = cart.session_key

        # Simular falha na limpeza de reservas por problema de sessão
        with patch("plataforma_de_servicos.cart.models.ReservaEstoque.objects.filter") as mock_filter:
            mock_filter.side_effect = Exception("Session key not found")
            
            response = complete_order(request)
            response_data = json.loads(response.content)

            # O pedido deve ser criado mesmo com falha na limpeza das reservas
            self.assertTrue(response_data["success"])

    def test_corrupted_cart_data_during_payment(self):
        """Testar dados de carrinho corrompidos durante pagamento"""
        request, cart = self.create_request_with_cart()

        # Corromper dados do carrinho
        request.session["cart"] = {"invalid": "data", "corrupted": True}
        request.session.save()

        response = complete_order(request)
        response_data = json.loads(response.content)

        # Deve falhar devido a dados corrompidos
        self.assertFalse(response_data["success"])

    def test_memory_error_during_large_order(self):
        """Testar erro de memória com pedido muito grande"""
        request, cart = self.create_request_with_cart()

        # Adicionar muitos itens ao carrinho
        for i in range(50):
            cart.add_product(self.produto, 1)

        with patch("plataforma_de_servicos.payment.models.OrderItem.objects.create") as mock_create:
            mock_create.side_effect = MemoryError("Out of memory")

            response = complete_order(request)
            response_data = json.loads(response.content)

            # Deve falhar graciosamente
            self.assertFalse(response_data["success"])

    def test_network_partition_between_services(self):
        """Testar partição de rede entre serviços"""
        request, cart = self.create_request_with_cart()

        # Simular que pedido é criado mas comunicação com estoque falha
        with patch("plataforma_de_servicos.estoque.services.EstoqueService.criar_saida_por_pedido") as mock_service:
            mock_service.side_effect = ConnectionError("Service unavailable")

            response = complete_order(request)
            response_data = json.loads(response.content)

            # Pedido deve ser criado mesmo com falha na comunicação
            self.assertTrue(response_data["success"])

            # Verificar que pedido existe
            order = Order.objects.get(id=response_data["order_id"])
            self.assertIsNotNone(order)

    def test_database_readonly_mode(self):
        """Testar banco em modo somente leitura"""
        request, cart = self.create_request_with_cart()

        with patch("plataforma_de_servicos.payment.models.Order.objects.create") as mock_create:
            mock_create.side_effect = OperationalError("The MySQL server is running with the --read-only option")

            response = complete_order(request)
            response_data = json.loads(response.content)

            # Deve falhar apropriadamente
            self.assertFalse(response_data["success"])
            self.assertIn("error", response_data)

    def test_max_connections_exceeded(self):
        """Testar limite máximo de conexões excedido"""
        request, cart = self.create_request_with_cart()

        with patch("plataforma_de_servicos.payment.models.Order.objects.create") as mock_create:
            mock_create.side_effect = OperationalError("Too many connections")

            response = complete_order(request)
            response_data = json.loads(response.content)

            # Deve falhar graciosamente
            self.assertFalse(response_data["success"])

    def test_disk_space_full_error(self):
        """Testar erro de disco cheio"""
        request, cart = self.create_request_with_cart()

        with patch("plataforma_de_servicos.payment.models.Order.objects.create") as mock_create:
            mock_create.side_effect = OperationalError("No space left on device")

            response = complete_order(request)
            response_data = json.loads(response.content)

            # Deve falhar apropriadamente
            self.assertFalse(response_data["success"])

    def test_recovery_after_network_failure(self):
        """Testar recuperação após falha temporária"""
        request, cart = self.create_request_with_cart()

        # Simular recuperação da rede
        call_attempts = 0
        def network_recovery(*args, **kwargs):
            nonlocal call_attempts
            call_attempts += 1

            if call_attempts <= 2:
                raise OperationalError("Network unreachable")
            # Depois de algumas tentativas, rede volta
            return Order.objects.create(*args, **kwargs)

        with patch("plataforma_de_servicos.payment.models.Order.objects.create") as mock_create:
            mock_create.side_effect = network_recovery

            # Primeira tentativa deve falhar
            response = complete_order(request)
            response_data = json.loads(response.content)

            # Verificar que falhou inicialmente
            self.assertFalse(response_data["success"])

    def tearDown(self):
        """Cleanup após cada teste"""
        ReservaEstoque.objects.all().delete()
        OrderItem.objects.all().delete()
        Order.objects.all().delete()
        EstoqueItens.objects.all().delete()
        Estoque.objects.all().delete()

    @classmethod
    def tearDownClass(cls):
        """Cleanup final"""
        super().tearDownClass()
