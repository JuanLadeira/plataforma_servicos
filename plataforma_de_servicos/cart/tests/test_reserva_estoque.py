import pytest
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from plataforma_de_servicos.cart.models import ReservaEstoque
from plataforma_de_servicos.produto.models import Produto, VariacaoProduto, Categoria

pytestmark = pytest.mark.cart


class ReservaEstoqueModelTest(TestCase):
    def setUp(self):
        """Configurar dados de teste"""
        ReservaEstoque.objects.all().delete()
        self.categoria = Categoria.objects.create(categoria="Eletrônicos")
        
        self.produto = Produto.objects.create(
            produto="Notebook",
            preco=Decimal("1500.00"),
            estoque=10,
            categoria=self.categoria
        )
        
        self.variacao = VariacaoProduto.objects.create(
            produto=self.produto,
            sku="NB001",
            preco=Decimal("1600.00"),
            estoque=5
        )
        
        self.session_key = "test_session_123"

    def test_criar_reserva_produto_simples(self):
        """Testar criação de reserva para produto simples"""
        reserva = ReservaEstoque.objects.create(
            session_key=self.session_key,
            produto=self.produto,
            quantidade=3
        )
        
        self.assertEqual(reserva.produto, self.produto)
        self.assertEqual(reserva.quantidade, 3)
        self.assertEqual(reserva.session_key, self.session_key)
        self.assertIsNotNone(reserva.expires_at)
        self.assertTrue(reserva.expires_at > timezone.now())

    def test_criar_reserva_variacao_produto(self):
        """Testar criação de reserva para variação de produto"""
        reserva = ReservaEstoque.objects.create(
            session_key=self.session_key,
            variacao_produto=self.variacao,
            quantidade=2
        )
        
        self.assertEqual(reserva.variacao_produto, self.variacao)
        self.assertEqual(reserva.quantidade, 2)
        self.assertIsNone(reserva.produto)

    def test_auto_expires_at(self):
        """Testar se expires_at é definido automaticamente"""
        antes = timezone.now()
        reserva = ReservaEstoque.objects.create(
            session_key=self.session_key,
            produto=self.produto,
            quantidade=1
        )
        depois = timezone.now()
        
        # Deve expirar em 30 minutos
        esperado_min = antes + timedelta(minutes=29)
        esperado_max = depois + timedelta(minutes=31)
        
        self.assertTrue(esperado_min <= reserva.expires_at <= esperado_max)

    def test_str_representation(self):
        """Testar representação string do modelo"""
        reserva_produto = ReservaEstoque.objects.create(
            session_key=self.session_key,
            produto=self.produto,
            quantidade=3
        )
        
        reserva_variacao = ReservaEstoque.objects.create(
            session_key=self.session_key,
            variacao_produto=self.variacao,
            quantidade=2
        )
        
        self.assertIn(self.produto.produto, str(reserva_produto))
        self.assertIn("3", str(reserva_produto))
        self.assertIn("2", str(reserva_variacao))

    def test_limpar_expiradas(self):
        """Testar remoção de reservas expiradas"""
        # Criar reserva expirada
        reserva_expirada = ReservaEstoque.objects.create(
            session_key=self.session_key,
            produto=self.produto,
            quantidade=1
        )
        reserva_expirada.expires_at = timezone.now() - timedelta(minutes=1)
        reserva_expirada.save()
        
        # Criar reserva válida
        reserva_valida = ReservaEstoque.objects.create(
            session_key="session_456",
            produto=self.produto,
            quantidade=2
        )
        
        # Verificar que temos 2 reservas
        self.assertEqual(ReservaEstoque.objects.count(), 2)
        
        # Limpar expiradas
        count, _ = ReservaEstoque.limpar_expiradas()
        
        # Verificar que apenas a expirada foi removida
        self.assertEqual(count, 1)
        self.assertEqual(ReservaEstoque.objects.count(), 1)
        self.assertTrue(ReservaEstoque.objects.filter(id=reserva_valida.id).exists())

    def test_get_quantidade_reservada_produto(self):
        """Testar cálculo de quantidade total reservada para produto"""
        # Criar múltiplas reservas para o mesmo produto
        ReservaEstoque.objects.create(
            session_key="session_1",
            produto=self.produto,
            quantidade=3
        )
        ReservaEstoque.objects.create(
            session_key="session_2",
            produto=self.produto,
            quantidade=2
        )
        
        # Criar reserva expirada (não deve contar)
        reserva_expirada = ReservaEstoque.objects.create(
            session_key="session_3",
            produto=self.produto,
            quantidade=5
        )
        reserva_expirada.expires_at = timezone.now() - timedelta(minutes=1)
        reserva_expirada.save()
        
        total_reservado = ReservaEstoque.get_quantidade_reservada(produto=self.produto)
        self.assertEqual(total_reservado, 5)  # 3 + 2, expirada não conta

    def test_get_quantidade_reservada_variacao(self):
        """Testar cálculo de quantidade total reservada para variação"""
        ReservaEstoque.objects.create(
            session_key="session_1",
            variacao_produto=self.variacao,
            quantidade=4
        )
        ReservaEstoque.objects.create(
            session_key="session_2",
            variacao_produto=self.variacao,
            quantidade=1
        )
        
        total_reservado = ReservaEstoque.get_quantidade_reservada(variacao_produto=self.variacao)
        self.assertEqual(total_reservado, 5)

    def test_unique_together_constraint(self):
        """Testar constraint unique_together"""
        # Primeira reserva
        ReservaEstoque.objects.create(
            session_key=self.session_key,
            produto=self.produto,
            quantidade=1
        )
        
        # Segunda reserva para mesmo session_key + produto deve falhar
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            ReservaEstoque.objects.create(
                session_key=self.session_key,
                produto=self.produto,
                quantidade=2
            )

    def test_quantidade_reservada_sem_reservas(self):
        """Testar retorno quando não há reservas"""
        total = ReservaEstoque.get_quantidade_reservada(produto=self.produto)
        self.assertEqual(total, 0)
        
        total_variacao = ReservaEstoque.get_quantidade_reservada(variacao_produto=self.variacao)
        self.assertEqual(total_variacao, 0)