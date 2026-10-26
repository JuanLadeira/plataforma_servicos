import pytest
from django.test import TestCase

from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.inventario.tests.factories import InventarioFactory
from plataforma_de_servicos.inventario.tests.factories import InventarioSaldoFactory
from plataforma_de_servicos.produto.tests.factories.atributos_factory import (
    AtributoFactory,
    ValorAtributoFactory,
    VariacaoProdutoFactory,
)
from plataforma_de_servicos.produto.tests.factories.produto_factory import ProdutoFactory

pytestmark = pytest.mark.inventario


class InventarioModelTest(TestCase):
    """Testes para o modelo Inventario."""

    def test_criar_inventario_com_valores_padrao(self):
        """Testar que inventário é criado com valores padrão corretos."""
        inventario = Inventario.objects.create(nome="Estoque Principal")

        self.assertTrue(inventario.is_ativo)
        self.assertFalse(inventario.exibir_na_vitrine)
        self.assertIsNotNone(inventario.slug)

    def test_criar_inventario_exibir_na_vitrine(self):
        """Testar criação de inventário com exibir_na_vitrine=True."""
        inventario = Inventario.objects.create(
            nome="Loja Física",
            exibir_na_vitrine=True,
        )

        self.assertTrue(inventario.exibir_na_vitrine)

    def test_factory_cria_inventario_com_exibir_na_vitrine_false(self):
        """Testar que a factory cria inventário com exibir_na_vitrine=False por padrão."""
        inventario = InventarioFactory()

        self.assertFalse(inventario.exibir_na_vitrine)

    def test_factory_cria_inventario_com_exibir_na_vitrine_true(self):
        """Testar que a factory aceita exibir_na_vitrine=True."""
        inventario = InventarioFactory(exibir_na_vitrine=True)

        self.assertTrue(inventario.exibir_na_vitrine)

    def test_filtrar_inventarios_exibiveis_na_vitrine(self):
        """Testar filtro de inventários que devem aparecer na vitrine."""
        inv_vitrine1 = InventarioFactory(exibir_na_vitrine=True, is_ativo=True)
        inv_vitrine2 = InventarioFactory(exibir_na_vitrine=True, is_ativo=True)
        inv_oculto = InventarioFactory(exibir_na_vitrine=False, is_ativo=True)
        inv_inativo = InventarioFactory(exibir_na_vitrine=True, is_ativo=False)

        # Filtrar inventários ativos e exibíveis na vitrine
        inventarios_vitrine = Inventario.objects.filter(
            is_ativo=True,
            exibir_na_vitrine=True,
        )

        self.assertEqual(inventarios_vitrine.count(), 2)
        self.assertIn(inv_vitrine1, inventarios_vitrine)
        self.assertIn(inv_vitrine2, inventarios_vitrine)
        self.assertNotIn(inv_oculto, inventarios_vitrine)
        self.assertNotIn(inv_inativo, inventarios_vitrine)

    def test_str_inventario(self):
        """Testar representação em string do inventário."""
        inventario = InventarioFactory(nome="Depósito Central")

        self.assertIn("Depósito Central", str(inventario))


class InventarioSaldoModelTest(TestCase):
    """Testes para o modelo InventarioSaldo com suporte a variação."""

    def test_criar_saldo_sem_variacao(self):
        """Testar criação de saldo apenas com produto (sem variação)."""
        inventario = InventarioFactory()
        produto = ProdutoFactory()

        saldo = InventarioSaldo.objects.create(
            inventario=inventario,
            produto=produto,
            quantidade=10,
        )

        self.assertEqual(saldo.quantidade, 10)
        self.assertIsNone(saldo.variacao)
        self.assertEqual(str(saldo), produto.produto)

    def test_criar_saldo_com_variacao(self):
        """Testar criação de saldo com variação."""
        inventario = InventarioFactory()
        variacao = VariacaoProdutoFactory()

        saldo = InventarioSaldo.objects.create(
            inventario=inventario,
            produto=variacao.produto,
            variacao=variacao,
            quantidade=5,
        )

        self.assertEqual(saldo.quantidade, 5)
        self.assertEqual(saldo.variacao, variacao)
        self.assertIn(variacao.produto.produto, str(saldo))

    def test_unique_together_produto_variacao(self):
        """Testar que unique_together inclui variação."""
        inventario = InventarioFactory()
        variacao = VariacaoProdutoFactory()

        InventarioSaldo.objects.create(
            inventario=inventario,
            produto=variacao.produto,
            variacao=variacao,
            quantidade=10,
        )

        # Tentar criar outro saldo com mesma combinação deve falhar
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            InventarioSaldo.objects.create(
                inventario=inventario,
                produto=variacao.produto,
                variacao=variacao,
                quantidade=5,
            )

    def test_saldos_diferentes_para_variacoes_diferentes(self):
        """Testar que variações diferentes do mesmo produto podem ter saldos separados."""
        inventario = InventarioFactory()
        produto = ProdutoFactory()

        # Criar atributos e valores diferentes para cada variação
        atributo = AtributoFactory(categoria=produto.categoria, nome="Tamanho")
        valor1 = ValorAtributoFactory(atributo=atributo, valor="P")
        valor2 = ValorAtributoFactory(atributo=atributo, valor="G")

        variacao1 = VariacaoProdutoFactory(produto=produto, estoque=0, valores=[valor1])
        variacao2 = VariacaoProdutoFactory(produto=produto, estoque=0, valores=[valor2])

        saldo1 = InventarioSaldo.objects.create(
            inventario=inventario,
            produto=produto,
            variacao=variacao1,
            quantidade=10,
        )

        saldo2 = InventarioSaldo.objects.create(
            inventario=inventario,
            produto=produto,
            variacao=variacao2,
            quantidade=20,
        )

        self.assertEqual(saldo1.quantidade, 10)
        self.assertEqual(saldo2.quantidade, 20)
        self.assertEqual(InventarioSaldo.objects.filter(produto=produto).count(), 2)

    def test_factory_inventario_saldo(self):
        """Testar que a factory cria InventarioSaldo corretamente."""
        saldo = InventarioSaldoFactory()

        self.assertIsNotNone(saldo.inventario)
        self.assertIsNotNone(saldo.produto)
        self.assertIsNone(saldo.variacao)
        self.assertGreater(saldo.quantidade, 0)

    def test_factory_inventario_saldo_com_variacao(self):
        """Testar que a factory aceita variação."""
        variacao = VariacaoProdutoFactory()
        saldo = InventarioSaldoFactory(
            produto=variacao.produto,
            variacao=variacao,
        )

        self.assertEqual(saldo.variacao, variacao)
        self.assertEqual(saldo.produto, variacao.produto)
