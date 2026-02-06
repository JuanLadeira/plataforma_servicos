"""
Testes unitários simples para modificadores de preço.
Evita usar factories e foca na funcionalidade core.
"""
import pytest
from decimal import Decimal
from django.test import TestCase

from ..models import Produto, Atributo, ValorAtributo, VariacaoProduto
from ..models.categoria_model import Categoria

pytestmark = pytest.mark.produto


class TestPriceModifiersCore(TestCase):
    """Testes core para modificadores de preço sem dependências externas"""

    def setUp(self):
        """Setup básico para todos os testes"""
        Atributo.objects.all().delete()
        self.categoria = Categoria.objects.create(categoria="Teste")
        self.produto = Produto.objects.create(
            produto="Produto Teste",
            preco=Decimal('100.00'),
            categoria=self.categoria,
            ncm="12345678"
        )
        # Atributos agora precisam estar vinculados a uma categoria
        self.cor_attr = Atributo.objects.create(nome="Cor", categoria=self.categoria)
        self.tam_attr = Atributo.objects.create(nome="Tamanho", categoria=self.categoria)

    def test_valor_atributo_default_modifiers(self):
        """Testa valores padrão dos modificadores"""
        valor = ValorAtributo.objects.create(atributo=self.cor_attr, valor="Azul")
        
        self.assertEqual(valor.preco_adicional, Decimal('0'))
        self.assertEqual(valor.percentual_adicional, Decimal('0'))

    def test_valor_atributo_with_fixed_price_modifier(self):
        """Testa valor com modificador de preço fixo"""
        valor = ValorAtributo.objects.create(
            atributo=self.cor_attr,
            valor="Premium", 
            preco_adicional=Decimal('15.00')
        )
        
        self.assertEqual(valor.preco_adicional, Decimal('15.00'))
        self.assertEqual(valor.percentual_adicional, Decimal('0'))

    def test_valor_atributo_with_percentage_modifier(self):
        """Testa valor com modificador percentual"""
        valor = ValorAtributo.objects.create(
            atributo=self.tam_attr,
            valor="GG",
            percentual_adicional=Decimal('25.00')
        )
        
        self.assertEqual(valor.preco_adicional, Decimal('0'))
        self.assertEqual(valor.percentual_adicional, Decimal('25.00'))

    def test_calcular_preco_final_no_modifiers(self):
        """Testa cálculo de preço sem modificadores"""
        valor = ValorAtributo.objects.create(atributo=self.cor_attr, valor="Normal")
        
        variacao = VariacaoProduto.objects.create(
            produto=self.produto,
            preco=Decimal('100.00'),
            estoque=10
        )
        variacao.valores.add(valor)
        
        preco_final = variacao.calcular_preco_final()
        self.assertEqual(preco_final, Decimal('100.00'))

    def test_calcular_preco_final_with_fixed_modifier(self):
        """Testa cálculo com modificador fixo"""
        valor = ValorAtributo.objects.create(
            atributo=self.cor_attr,
            valor="Premium",
            preco_adicional=Decimal('25.00')
        )
        
        variacao = VariacaoProduto.objects.create(
            produto=self.produto,
            preco=Decimal('100.00'),
            estoque=10
        )
        variacao.valores.add(valor)
        
        preco_final = variacao.calcular_preco_final()
        # 100 + 25 = 125
        self.assertEqual(preco_final, Decimal('125.00'))

    def test_calcular_preco_final_with_percentage_modifier(self):
        """Testa cálculo com modificador percentual"""
        valor = ValorAtributo.objects.create(
            atributo=self.tam_attr,
            valor="XL",
            percentual_adicional=Decimal('20.00')
        )
        
        variacao = VariacaoProduto.objects.create(
            produto=self.produto,
            preco=Decimal('50.00'),
            estoque=10
        )
        variacao.valores.add(valor)
        
        preco_final = variacao.calcular_preco_final()
        # 50 + (50 * 0.20) = 50 + 10 = 60
        self.assertEqual(preco_final, Decimal('60.00'))

    def test_calcular_preco_final_with_both_modifiers(self):
        """Testa cálculo com ambos modificadores"""
        material_attr = Atributo.objects.create(nome="Material", categoria=self.categoria)
        valor = ValorAtributo.objects.create(
            atributo=material_attr,
            valor="Premium",
            preco_adicional=Decimal('10.00'),
            percentual_adicional=Decimal('15.00')
        )
        
        variacao = VariacaoProduto.objects.create(
            produto=self.produto,
            preco=Decimal('80.00'),
            estoque=10
        )
        variacao.valores.add(valor)
        
        preco_final = variacao.calcular_preco_final()
        # 80 + 10 + (80 * 0.15) = 80 + 10 + 12 = 102
        self.assertEqual(preco_final, Decimal('102.00'))

    def test_calcular_preco_final_multiple_attributes(self):
        """Testa cálculo com múltiplos atributos"""
        # Cor com preço adicional
        cor_valor = ValorAtributo.objects.create(
            atributo=self.cor_attr,
            valor="Dourado",
            preco_adicional=Decimal('30.00')
        )
        
        # Tamanho com percentual
        tam_valor = ValorAtributo.objects.create(
            atributo=self.tam_attr,
            valor="G",
            percentual_adicional=Decimal('10.00')
        )
        
        variacao = VariacaoProduto.objects.create(
            produto=self.produto,
            preco=Decimal('100.00'),
            estoque=10
        )
        variacao.valores.add(cor_valor, tam_valor)
        
        preco_final = variacao.calcular_preco_final()
        # 100 + 30 + (100 * 0.10) = 100 + 30 + 10 = 140
        self.assertEqual(preco_final, Decimal('140.00'))

    def test_calcular_preco_final_fallback_to_produto_price(self):
        """Testa fallback para preço do produto quando variação tem preço None"""
        valor = ValorAtributo.objects.create(
            atributo=self.cor_attr,
            valor="Normal",
            preco_adicional=Decimal('5.00')
        )
        
        # Variação sem preço definido
        variacao = VariacaoProduto.objects.create(
            produto=self.produto,
            preco=None,
            estoque=10
        )
        variacao.valores.add(valor)
        
        preco_final = variacao.calcular_preco_final()
        # Usa preço do produto: 100 + 5 = 105
        self.assertEqual(preco_final, Decimal('105.00'))

    def test_calcular_preco_final_no_price_returns_zero(self):
        """Testa comportamento quando nem produto nem variação têm preço"""
        produto_sem_preco = Produto.objects.create(
            produto="Produto Sem Preço",
            preco=None,
            categoria=self.categoria,
            ncm="87654321"
        )
        
        valor = ValorAtributo.objects.create(
            atributo=self.cor_attr,
            valor="Qualquer",
            preco_adicional=Decimal('10.00'),
            percentual_adicional=Decimal('20.00')
        )
        
        variacao = VariacaoProduto.objects.create(
            produto=produto_sem_preco,
            preco=None,
            estoque=10
        )
        variacao.valores.add(valor)
        
        preco_final = variacao.calcular_preco_final()
        self.assertEqual(preco_final, Decimal('0.00'))

    def test_get_preco_display_formatting(self):
        """Testa formatação do preço para exibição"""
        valor = ValorAtributo.objects.create(
            atributo=self.cor_attr,
            valor="Premium",
            preco_adicional=Decimal('234.56')
        )
        
        variacao = VariacaoProduto.objects.create(
            produto=self.produto,
            preco=Decimal('1000.00'),
            estoque=10
        )
        variacao.valores.add(valor)
        
        # 1000 + 234.56 = 1234.56
        preco_display = variacao.get_preco_display()
        self.assertEqual(preco_display, "R$ 1.234,56")

    def test_calcular_preco_final_decimal_precision(self):
        """Testa precisão decimal nos cálculos"""
        desconto_attr = Atributo.objects.create(nome="Desconto", categoria=self.categoria)
        valor = ValorAtributo.objects.create(
            atributo=desconto_attr,
            valor="Especial",
            percentual_adicional=Decimal('33.33')  # Vai gerar casas decimais
        )
        
        variacao = VariacaoProduto.objects.create(
            produto=self.produto,
            preco=Decimal('30.00'),
            estoque=10
        )
        variacao.valores.add(valor)
        
        preco_final = variacao.calcular_preco_final()
        # 30.00 + (30.00 * 0.3333) = 30.00 + 9.999 = 39.999 -> 40.00 (arredondado)
        self.assertEqual(preco_final, Decimal('40.00'))
        
        # Verifica que tem exatamente 2 casas decimais
        self.assertEqual(preco_final.as_tuple().exponent, -2)

    def test_valor_atributo_str_representation(self):
        """Testa representação string do ValorAtributo"""
        valor = ValorAtributo.objects.create(atributo=self.cor_attr, valor="Azul")
        
        self.assertEqual(str(valor), "Cor: Azul")

    def test_variacao_produto_str_with_valores(self):
        """Testa representação string da VariacaoProduto com valores"""
        cor_valor = ValorAtributo.objects.create(atributo=self.cor_attr, valor="Verde")
        
        tam_valor = ValorAtributo.objects.create(atributo=self.tam_attr, valor="M")
        
        variacao = VariacaoProduto.objects.create(
            produto=self.produto,
            preco=Decimal('50.00'),
            estoque=10
        )
        variacao.valores.add(cor_valor, tam_valor)
        
        str_repr = str(variacao)
        self.assertIn("Produto Teste", str_repr)
        self.assertIn("Cor: Verde", str_repr)
        self.assertIn("Tamanho: M", str_repr)
