import pytest
from django.test import TestCase

from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.inventario.tests.factories import InventarioFactory
from plataforma_de_servicos.produto.tests.factories.produto_factory import ProdutoFactory

pytestmark = pytest.mark.inventario


class InventarioSignalTest(TestCase):
    def test_signal_atualiza_disponibilidade_produto(self):
        """
        Testar que o sinal post_save em InventarioSaldo atualiza
        corretamente o campo 'disponivel' do produto.
        """
        produto = ProdutoFactory(disponivel=False)
        inventario_vitrine = InventarioFactory(exibir_na_vitrine=True, is_ativo=True)
        inventario_oculto = InventarioFactory(exibir_na_vitrine=False, is_ativo=True)

        # 1. Adicionar saldo em inventário de vitrine -> produto deve ficar disponível
        saldo = InventarioSaldo.objects.create(
            inventario=inventario_vitrine,
            produto=produto,
            quantidade=10,
        )
        produto.refresh_from_db()
        self.assertTrue(produto.disponivel)

        # 2. Mudar saldo para zero -> produto deve ficar indisponível
        saldo.quantidade = 0
        saldo.save()
        produto.refresh_from_db()
        self.assertFalse(produto.disponivel)

        # 3. Adicionar saldo novamente -> produto deve ficar disponível
        saldo.quantidade = 5
        saldo.save()
        produto.refresh_from_db()
        self.assertTrue(produto.disponivel)

        # 4. Adicionar saldo em um segundo inventário de vitrine
        outro_inventario_vitrine = InventarioFactory(exibir_na_vitrine=True, is_ativo=True)
        outro_saldo = InventarioSaldo.objects.create(
            inventario=outro_inventario_vitrine,
            produto=produto,
            quantidade=3,
        )
        produto.refresh_from_db()
        self.assertTrue(produto.disponivel)

        # 5. Remover saldo do primeiro inventário -> produto deve continuar disponível
        saldo.quantidade = 0
        saldo.save()
        produto.refresh_from_db()
        self.assertTrue(produto.disponivel)

        # 6. Remover saldo do segundo inventário -> produto deve ficar indisponível
        outro_saldo.quantidade = 0
        outro_saldo.save()
        produto.refresh_from_db()
        self.assertFalse(produto.disponivel)

        # 7. Adicionar saldo em inventário que não é vitrine -> produto não deve ficar disponível
        saldo_oculto = InventarioSaldo.objects.create(
            inventario=inventario_oculto,
            produto=produto,
            quantidade=10,
        )
        produto.refresh_from_db()
        self.assertFalse(produto.disponivel)
