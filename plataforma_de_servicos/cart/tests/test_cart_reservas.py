from decimal import Decimal
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from django.test import TestCase

from plataforma_de_servicos.cart.cart import Cart
from plataforma_de_servicos.cart.models import ReservaEstoque
from plataforma_de_servicos.produto.models import Categoria
from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.produto.models import VariacaoProduto

pytestmark = pytest.mark.cart


class CartComReservasTest(TestCase):
    def setUp(self):
        """Configurar dados de teste"""
        self.factory = RequestFactory()
        
        # Limpar reservas de testes anteriores que podem ter vazado de threads
        ReservaEstoque.objects.all().delete()

        self.categoria = Categoria.objects.create(categoria="Eletrônicos")

        self.produto = Produto.objects.create(
            produto="Smartphone",
            preco=Decimal("800.00"),
            estoque=15,
            categoria=self.categoria,
        )

        self.variacao = VariacaoProduto.objects.create(
            produto=self.produto,
            sku="SM001",
            preco=Decimal("850.00"),
            estoque=8,
        )

    def create_request_with_session(self):
        """Criar request com sessão configurada"""
        request = self.factory.get("/")
        middleware = SessionMiddleware(MagicMock())
        middleware.process_request(request)
        request.session.save()
        return request

    def test_add_produto_cria_reserva(self):
        """Testar que adicionar produto cria reserva"""
        request = self.create_request_with_session()
        cart = Cart(request)

        # Verificar que não há reservas inicialmente
        self.assertEqual(ReservaEstoque.objects.count(), 0)

        # Adicionar produto ao carrinho
        cart.add_product(self.produto, 3)

        # Verificar que reserva foi criada
        self.assertEqual(ReservaEstoque.objects.count(), 1)
        reserva = ReservaEstoque.objects.first()
        self.assertEqual(reserva.produto, self.produto)
        self.assertEqual(reserva.quantidade, 3)
        self.assertEqual(reserva.session_key, cart.session_key)

    def test_add_variacao_cria_reserva(self):
        """Testar que adicionar variação cria reserva"""
        request = self.create_request_with_session()
        cart = Cart(request)

        cart.add(self.variacao, 2)

        self.assertEqual(ReservaEstoque.objects.count(), 1)
        reserva = ReservaEstoque.objects.first()
        self.assertEqual(reserva.variacao_produto, self.variacao)
        self.assertEqual(reserva.quantidade, 2)

    def test_add_incrementa_reserva_existente(self):
        """Testar que adicionar mais do mesmo produto incrementa reserva"""
        request = self.create_request_with_session()
        cart = Cart(request)

        # Adicionar produto duas vezes
        cart.add_product(self.produto, 2)
        cart.add_product(self.produto, 1)

        # Deve haver apenas uma reserva com quantidade total
        self.assertEqual(ReservaEstoque.objects.count(), 1)
        reserva = ReservaEstoque.objects.first()
        self.assertEqual(reserva.quantidade, 3)

    def test_update_atualiza_reserva(self):
        """Testar que atualizar quantidade atualiza reserva"""
        request = self.create_request_with_session()
        cart = Cart(request)

        # Adicionar produto
        cart.add_product(self.produto, 2)

        # Atualizar quantidade
        product_key = f"produto_{self.produto.id}"
        cart.update(product_key, 5)

        # Verificar reserva atualizada
        reserva = ReservaEstoque.objects.first()
        self.assertEqual(reserva.quantidade, 5)

    def test_delete_remove_reserva(self):
        """Testar que remover item remove reserva"""
        request = self.create_request_with_session()
        cart = Cart(request)

        # Adicionar produto
        cart.add_product(self.produto, 2)
        self.assertEqual(ReservaEstoque.objects.count(), 1)

        # Remover produto
        product_key = f"produto_{self.produto.id}"
        cart.delete(product_key)

        # Verificar que reserva foi removida
        self.assertEqual(ReservaEstoque.objects.count(), 0)

    def test_clear_remove_todas_reservas(self):
        """Testar que limpar carrinho remove todas as reservas"""
        request = self.create_request_with_session()
        cart = Cart(request)

        # Adicionar múltiplos produtos
        cart.add_product(self.produto, 2)
        cart.add(self.variacao, 1)

        self.assertEqual(ReservaEstoque.objects.count(), 2)

        # Limpar carrinho
        cart.clear()

        # Verificar que todas as reservas foram removidas
        self.assertEqual(ReservaEstoque.objects.count(), 0)
        self.assertEqual(len(cart.cart), 0)

    @patch("plataforma_de_servicos.cart.models.timezone")
    @patch("plataforma_de_servicos.cart.cart.timezone")
    def test_reserva_expira_automaticamente(self, mock_cart_timezone, mock_models_timezone):
        """Testar que reservas expiram em 30 minutos"""
        from datetime import timedelta

        from django.utils import timezone

        now = timezone.now()
        # Mock timezone para ambos os locais onde é usado
        mock_cart_timezone.now.return_value = now
        mock_cart_timezone.timedelta = timedelta
        mock_models_timezone.now.return_value = now

        request = self.create_request_with_session()
        cart = Cart(request)

        cart.add_product(self.produto, 1)

        reserva = ReservaEstoque.objects.first()
        expected_expiry = now + timedelta(minutes=30)

        # Verificar que a expiração foi definida corretamente
        self.assertEqual(reserva.expires_at, expected_expiry)

    def test_session_key_gerado_automaticamente(self):
        """Testar que session_key é gerado se não existir"""
        request = self.factory.get("/")

        # Não configurar sessão completamente
        middleware = SessionMiddleware(MagicMock())
        middleware.process_request(request)

        # Session key inicialmente não existe
        self.assertIsNone(request.session.session_key)

        cart = Cart(request)

        # Depois de criar Cart, session_key deve existir
        self.assertIsNotNone(cart.session_key)
        self.assertIsNotNone(request.session.session_key)

    def test_erro_na_criacao_reserva_nao_quebra_carrinho(self):
        """Testar que erro na criação de reserva não quebra funcionamento do carrinho"""
        request = self.create_request_with_session()
        cart = Cart(request)

        # Mock que simula erro na criação da reserva
        with patch("plataforma_de_servicos.cart.models.ReservaEstoque.objects.get_or_create") as mock_create:
            mock_create.side_effect = Exception("Erro de banco")

            # Adicionar produto deve funcionar mesmo com erro na reserva
            cart.add_product(self.produto, 1)

            # Carrinho deve conter o produto
            self.assertEqual(len(cart), 1)

    def test_multiple_sessions_reservas_separadas(self):
        """Testar que diferentes sessões têm reservas separadas"""
        request1 = self.create_request_with_session()
        request2 = self.create_request_with_session()

        cart1 = Cart(request1)
        cart2 = Cart(request2)

        # Adicionar mesmo produto em carrinho diferentes
        cart1.add_product(self.produto, 2)
        cart2.add_product(self.produto, 3)

        # Deve haver duas reservas distintas
        self.assertEqual(ReservaEstoque.objects.count(), 2)

        reservas = ReservaEstoque.objects.all()
        session_keys = [r.session_key for r in reservas]
        quantidades = [r.quantidade for r in reservas]

        self.assertIn(cart1.session_key, session_keys)
        self.assertIn(cart2.session_key, session_keys)
        self.assertIn(2, quantidades)
        self.assertIn(3, quantidades)

    def test_iter_funciona_com_produtos_e_variacoes(self):
        """Testar que iteração do carrinho funciona com produtos e variações misturados"""
        request = self.create_request_with_session()
        cart = Cart(request)

        # Adicionar produto simples e variação
        cart.add_product(self.produto, 1)
        cart.add(self.variacao, 2)

        items = list(cart)
        self.assertEqual(len(items), 2)

        # Verificar que ambos têm informações corretas
        for item in items:
            self.assertIn("preco", item)
            self.assertIn("qty", item)
            self.assertIn("total", item)

        # Um deve ter 'produto' e outro 'variation'
        has_produto = any("produto" in item for item in items)
        has_variation = any("variation" in item for item in items)
        self.assertTrue(has_produto)
        self.assertTrue(has_variation)
