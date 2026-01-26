import pytest
from django.test import TestCase

from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.inventario.tests.factories import InventarioFactory

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
