import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from unittest.mock import patch

from plataforma_de_servicos.estoque.services import EstoqueService
from plataforma_de_servicos.estoque.models import Estoque, EstoqueItens
from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.estoque.choices.origem_saida import OrigemSaida
from plataforma_de_servicos.produto.models import Produto, VariacaoProduto, Categoria
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.cart.models import ReservaEstoque

pytestmark = pytest.mark.estoque

User = get_user_model()


class EstoqueServiceTest(TestCase):
    def setUp(self):
        """Configurar dados de teste"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.inventario = Inventario.objects.create(
            nome="Estoque Principal"
        )
        
        self.categoria = Categoria.objects.create(categoria="Eletrônicos")
        
        self.produto1 = Produto.objects.create(
            produto="Notebook Dell",
            preco=Decimal("1500.00"),
            estoque=10,
            categoria=self.categoria
        )
        
        self.produto2 = Produto.objects.create(
            produto="Mouse",
            preco=Decimal("50.00"),
            estoque=20,
            categoria=self.categoria
        )
        
        self.variacao = VariacaoProduto.objects.create(
            produto=self.produto1,
            sku="DELL001",
            preco=Decimal("1600.00"),
            estoque=5
        )

    def test_criar_saida_por_pedido(self):
        """Testar criação de saída de estoque para pedido"""
        pedido_id = 123
        itens_pedido = [
            {
                'produto': self.produto1,
                'quantidade': 2,
                'variacao': None
            },
            {
                'produto': self.produto2,
                'quantidade': 1,
                'variacao': None
            }
        ]
        
        estoque_inicial_p1 = self.produto1.estoque
        estoque_inicial_p2 = self.produto2.estoque
        
        saida = EstoqueService.criar_saida_por_pedido(
            pedido_id=pedido_id,
            itens_pedido=itens_pedido,
            funcionario=self.user,
            inventario_origem=self.inventario
        )
        
        # Verificar criação do registro de saída
        self.assertIsInstance(saida, Estoque)
        self.assertEqual(saida.movimento, Movimento.SAIDA.value)
        self.assertEqual(saida.origem_saida, OrigemSaida.PEDIDO.value)
        self.assertEqual(saida.pedido_id, pedido_id)
        self.assertEqual(saida.funcionario, self.user)
        self.assertEqual(saida.inventario_origem, self.inventario)
        self.assertTrue(saida.processado)
        
        # Verificar criação dos itens
        itens = EstoqueItens.objects.filter(estoque=saida)
        self.assertEqual(itens.count(), 2)
        
        item1 = itens.get(produto=self.produto1)
        item2 = itens.get(produto=self.produto2)
        self.assertEqual(item1.quantidade, 2)
        self.assertEqual(item2.quantidade, 1)
        
        # Verificar atualização do estoque
        self.produto1.refresh_from_db()
        self.produto2.refresh_from_db()
        self.assertEqual(self.produto1.estoque, estoque_inicial_p1 - 2)
        self.assertEqual(self.produto2.estoque, estoque_inicial_p2 - 1)

    def test_criar_saida_por_pedido_com_variacao(self):
        """Testar criação de saída com variações de produto"""
        pedido_id = 456
        itens_pedido = [
            {
                'produto': self.produto1,
                'quantidade': 1,
                'variacao': self.variacao
            }
        ]
        
        saida = EstoqueService.criar_saida_por_pedido(
            pedido_id=pedido_id,
            itens_pedido=itens_pedido,
            funcionario=self.user
        )
        
        self.assertEqual(saida.pedido_id, pedido_id)
        
        # Verificar que o produto foi usado (não a variação)
        item = EstoqueItens.objects.get(estoque=saida)
        self.assertEqual(item.produto, self.produto1)
        self.assertEqual(item.quantidade, 1)

    def test_criar_saida_manual(self):
        """Testar criação de saída manual"""
        itens = [
            {'produto': self.produto1, 'quantidade': 3},
            {'produto': self.produto2, 'quantidade': 2}
        ]
        
        observacao = "Produtos danificados durante transporte"
        
        saida = EstoqueService.criar_saida_manual(
            origem=OrigemSaida.PERDA.value,
            itens=itens,
            funcionario=self.user,
            inventario_origem=self.inventario,
            observacao=observacao
        )
        
        # Verificar saída criada
        self.assertEqual(saida.movimento, Movimento.SAIDA.value)
        self.assertEqual(saida.origem_saida, OrigemSaida.PERDA.value)
        self.assertEqual(saida.funcionario, self.user)
        self.assertEqual(saida.observacao, observacao)
        self.assertIsNone(saida.pedido_id)
        self.assertFalse(saida.processado)  # Manual não processa automaticamente
        
        # Verificar itens
        itens_estoque = EstoqueItens.objects.filter(estoque=saida)
        self.assertEqual(itens_estoque.count(), 2)

    def test_liberar_reserva_para_saida(self):
        """Testar conversão de reservas em saída de estoque"""
        session_key = "test_session_789"
        
        # Criar reservas
        reserva1 = ReservaEstoque.objects.create(
            session_key=session_key,
            produto=self.produto1,
            quantidade=2
        )
        
        reserva2 = ReservaEstoque.objects.create(
            session_key=session_key,
            variacao_produto=self.variacao,
            quantidade=1
        )
        
        reservas = [reserva1, reserva2]
        pedido_id = 789
        
        saida = EstoqueService.liberar_reserva_para_saida(
            reservas_carrinho=reservas,
            pedido_id=pedido_id,
            funcionario=self.user
        )
        
        # Verificar saída criada
        self.assertEqual(saida.pedido_id, pedido_id)
        self.assertEqual(saida.origem_saida, OrigemSaida.PEDIDO.value)
        
        # Verificar itens criados
        itens = EstoqueItens.objects.filter(estoque=saida)
        self.assertEqual(itens.count(), 2)
        
        # Como ambas as reservas se referem ao mesmo produto base, devemos ter 2 itens separados
        item1 = itens.filter(produto=self.produto1, quantidade=2).first()
        item2 = itens.filter(produto=self.produto1, quantidade=1).first()
        
        self.assertIsNotNone(item1, "Item da reserva do produto simples deve existir")
        self.assertIsNotNone(item2, "Item da reserva da variação deve existir")
        self.assertEqual(item1.quantidade, 2)
        self.assertEqual(item2.quantidade, 1)

    @patch('plataforma_de_servicos.inventario.models.Inventario.objects.first')
    def test_criar_saida_sem_inventario(self, mock_inventario):
        """Testar criação quando inventario_origem é None"""
        mock_inventario.return_value = self.inventario
        
        itens_pedido = [{'produto': self.produto1, 'quantidade': 1, 'variacao': None}]
        
        saida = EstoqueService.criar_saida_por_pedido(
            pedido_id=999,
            itens_pedido=itens_pedido,
            funcionario=self.user,
            inventario_origem=None  # Deve usar o primeiro inventário
        )
        
        self.assertEqual(saida.inventario_origem, self.inventario)
        mock_inventario.assert_called_once()

    def test_criar_saida_observacao_automatica(self):
        """Testar se observação é gerada automaticamente"""
        pedido_id = 555
        itens_pedido = [{'produto': self.produto1, 'quantidade': 1, 'variacao': None}]
        
        saida = EstoqueService.criar_saida_por_pedido(
            pedido_id=pedido_id,
            itens_pedido=itens_pedido
        )
        
        self.assertIn(str(pedido_id), saida.observacao)
        self.assertIn("Saída automática", saida.observacao)

    def test_transacao_atomica_falha(self):
        """Testar que falhas mantêm consistência transacional"""
        # Criar produto com estoque insuficiente
        produto_sem_estoque = Produto.objects.create(
            produto="Produto Sem Estoque",
            preco=Decimal("100.00"),
            estoque=0,
            categoria=self.categoria
        )
        
        itens_pedido = [{'produto': produto_sem_estoque, 'quantidade': 5, 'variacao': None}]
        
        # Tentar criar saída deve falhar por estoque insuficiente
        with self.assertRaises(Exception):
            EstoqueService.criar_saida_por_pedido(
                pedido_id=777,
                itens_pedido=itens_pedido
            )
        
        # Verificar que nenhum registro foi criado
        self.assertEqual(
            Estoque.objects.filter(pedido_id=777).count(), 
            0
        )