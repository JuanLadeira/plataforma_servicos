import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from decimal import Decimal

from plataforma_de_servicos.estoque.models import Estoque, EstoqueItens
from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.estoque.choices.origem_saida import OrigemSaida
from plataforma_de_servicos.produto.models import Produto, Categoria
from plataforma_de_servicos.inventario.models import Inventario

pytestmark = pytest.mark.estoque

User = get_user_model()


class EstoqueModelTest(TestCase):
    def setUp(self):
        """Configurar dados de teste"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.inventario_origem = Inventario.objects.create(
            nome="Estoque Loja A",
        )
        
        self.inventario_destino = Inventario.objects.create(
            nome="Estoque Loja B",
        )
        
        self.categoria = Categoria.objects.create(categoria="Eletrônicos")
        
        self.produto = Produto.objects.create(
            produto="Monitor",
            preco=Decimal("500.00"),
            estoque=15,
            categoria=self.categoria
        )

    def test_criar_saida_com_origem_pedido(self):
        """Testar criação de saída com origem pedido"""
        estoque = Estoque.objects.create(
            funcionario=self.user,
            movimento=Movimento.SAIDA.value,
            origem_saida=OrigemSaida.PEDIDO.value,
            pedido_id=123,
            inventario_origem=self.inventario_origem,
            observacao="Saída para pedido #123"
        )
        
        self.assertEqual(estoque.origem_saida, OrigemSaida.PEDIDO.value)
        self.assertEqual(estoque.pedido_id, 123)
        self.assertFalse(estoque.processado)
        self.assertIn("123", estoque.observacao)

    def test_criar_saida_com_origem_perda(self):
        """Testar criação de saída com origem perda"""
        estoque = Estoque.objects.create(
            funcionario=self.user,
            movimento=Movimento.SAIDA.value,
            origem_saida=OrigemSaida.PERDA.value,
            inventario_origem=self.inventario_origem,
            observacao="Produtos danificados"
        )
        
        self.assertEqual(estoque.origem_saida, OrigemSaida.PERDA.value)
        self.assertIsNone(estoque.pedido_id)
        self.assertEqual(estoque.observacao, "Produtos danificados")

    def test_validacao_saida_sem_origem(self):
        """Testar que saída sem origem_saida é válida (campo opcional para saídas manuais)"""
        estoque = Estoque(
            funcionario=self.user,
            movimento=Movimento.SAIDA.value,
            # origem_saida não definida - agora é opcional
            inventario_origem=self.inventario_origem
        )

        # Não deve levantar exceção - origem_saida é opcional
        estoque.clean()
        self.assertIsNone(estoque.origem_saida)

    def test_validacao_pedido_sem_id(self):
        """Testar que saída por pedido sem pedido_id falha na validação"""
        estoque = Estoque(
            funcionario=self.user,
            movimento=Movimento.SAIDA.value,
            origem_saida=OrigemSaida.PEDIDO.value,
            inventario_origem=self.inventario_origem,
            # pedido_id não definido
        )
        
        with self.assertRaises(ValidationError) as context:
            estoque.clean()
        
        self.assertIn("Saída por pedido requer ID do pedido", str(context.exception))

    def test_validacao_entrada_sem_origem_saida(self):
        """Testar que entrada não precisa de origem_saida"""
        estoque = Estoque(
            funcionario=self.user,
            movimento=Movimento.ENTRADA.value,
            inventario_destino=self.inventario_destino,
            # origem_saida não definida - deve ser OK para entrada
        )
        
        # Não deve levantar exceção
        try:
            estoque.clean()
        except ValidationError:
            self.fail("Entrada não deveria requerer origem_saida")

    def test_validacao_transferencia_sem_origem_saida(self):
        """Testar que transferência não precisa de origem_saida"""
        estoque = Estoque(
            funcionario=self.user,
            movimento=Movimento.TRANSFERENCIA.value,
            inventario_origem=self.inventario_origem,
            inventario_destino=self.inventario_destino,
            # origem_saida não definida - deve ser OK para transferência
        )
        
        try:
            estoque.clean()
        except ValidationError:
            self.fail("Transferência não deveria requerer origem_saida")

    def test_todas_opcoes_origem_saida(self):
        """Testar todas as opções de origem_saida"""
        opcoes = [
            OrigemSaida.PEDIDO.value,
            OrigemSaida.PERDA.value,
            OrigemSaida.DEVOLUCAO.value,
            OrigemSaida.AJUSTE.value,
            OrigemSaida.TRANSFERENCIA.value,
            OrigemSaida.OUTROS.value
        ]
        
        for origem in opcoes:
            with self.subTest(origem=origem):
                estoque = Estoque.objects.create(
                    funcionario=self.user,
                    movimento=Movimento.SAIDA.value,
                    origem_saida=origem,
                    inventario_origem=self.inventario_origem,
                    pedido_id=999 if origem == OrigemSaida.PEDIDO.value else None
                )
                
                self.assertEqual(estoque.origem_saida, origem)

    def test_processar_saida_com_origem_pedido(self):
        """Testar processamento de saída com origem pedido"""
        estoque = Estoque.objects.create(
            funcionario=self.user,
            movimento=Movimento.SAIDA.value,
            origem_saida=OrigemSaida.PEDIDO.value,
            pedido_id=456,
            inventario_origem=self.inventario_origem
        )
        
        # Criar item de estoque
        EstoqueItens.objects.create(
            estoque=estoque,
            produto=self.produto,
            quantidade=3,
            inventario=self.inventario_origem
        )
        
        estoque_inicial = self.produto.estoque
        
        # Processar saída
        estoque.processar()
        
        # Verificar que foi processado
        self.assertTrue(estoque.processado)
        
        # Verificar que estoque foi reduzido
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, estoque_inicial - 3)

    def test_str_representation_com_observacao(self):
        """Testar representação string com observação"""
        estoque = Estoque.objects.create(
            funcionario=self.user,
            nf=123,
            movimento=Movimento.SAIDA.value,
            origem_saida=OrigemSaida.PEDIDO.value,
            pedido_id=789,
            inventario_origem=self.inventario_origem,
            observacao="Pedido urgente"
        )
        
        str_repr = str(estoque)
        self.assertIn("123", str_repr)  # NF
        self.assertIn(str(estoque.pk), str_repr)  # ID

    def test_campos_opcionais(self):
        """Testar que campos opcionais podem ser None/blank"""
        estoque = Estoque.objects.create(
            funcionario=self.user,
            movimento=Movimento.ENTRADA.value,
            inventario_destino=self.inventario_destino,
            # nf, origem_saida, pedido_id, observacao são opcionais
        )
        
        self.assertIsNone(estoque.nf)
        self.assertIsNone(estoque.origem_saida)
        self.assertIsNone(estoque.pedido_id)
        self.assertIsNone(estoque.observacao)

    def test_help_text_campos(self):
        """Testar que help_text está definido corretamente"""
        estoque = Estoque()
        
        origem_field = estoque._meta.get_field('origem_saida')
        pedido_field = estoque._meta.get_field('pedido_id')
        observacao_field = estoque._meta.get_field('observacao')
        
        self.assertIn("Motivo/origem da saída", origem_field.help_text)
        self.assertIn("ID do pedido quando", pedido_field.help_text)
        self.assertIn("Observações adicionais", observacao_field.help_text)

    def test_max_length_origem_saida(self):
        """Testar que max_length de origem_saida está correto"""
        origem_field = Estoque._meta.get_field('origem_saida')
        self.assertEqual(origem_field.max_length, 15)

    def test_choices_origem_saida(self):
        """Testar que choices estão definidas corretamente"""
        origem_field = Estoque._meta.get_field('origem_saida')
        expected_choices = OrigemSaida.choices
        self.assertEqual(origem_field.choices, expected_choices)