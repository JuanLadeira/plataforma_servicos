import pytest
from django.test import Client
from django.test import TestCase
from django.urls import reverse

from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.inventario.tests.factories import InventarioFactory
from plataforma_de_servicos.produto.tests.factories.categoria_factory import CategoriaFactory
from plataforma_de_servicos.produto.tests.factories.produto_factory import ProdutoFactory

pytestmark = pytest.mark.inventario


class HomeVitrineFilterTest(TestCase):
    """Testes para o filtro de produtos por inventário na home."""

    def setUp(self):
        self.client = Client()
        self.categoria = CategoriaFactory()

        # Inventário que deve aparecer na vitrine
        self.inventario_vitrine = InventarioFactory(
            nome="Loja Principal",
            is_ativo=True,
            exibir_na_vitrine=True,
        )

        # Inventário que NÃO deve aparecer na vitrine
        self.inventario_oculto = InventarioFactory(
            nome="Depósito Interno",
            is_ativo=True,
            exibir_na_vitrine=False,
        )

        # Inventário inativo (não deve aparecer)
        self.inventario_inativo = InventarioFactory(
            nome="Loja Fechada",
            is_ativo=False,
            exibir_na_vitrine=True,
        )

        # Produto na vitrine (tem saldo em inventário com exibir_na_vitrine=True)
        self.produto_vitrine = ProdutoFactory(
            produto="Produto Vitrine",
            categoria=self.categoria,
            estoque=10,
            preco=99.90,
        )
        InventarioSaldo.objects.create(
            inventario=self.inventario_vitrine,
            produto=self.produto_vitrine,
            quantidade=10,
        )

        # Produto oculto (tem saldo apenas em inventário com exibir_na_vitrine=False)
        self.produto_oculto = ProdutoFactory(
            produto="Produto Oculto",
            categoria=self.categoria,
            estoque=5,
            preco=49.90,
        )
        InventarioSaldo.objects.create(
            inventario=self.inventario_oculto,
            produto=self.produto_oculto,
            quantidade=5,
        )

        # Produto em inventário inativo (não deve aparecer)
        self.produto_inativo = ProdutoFactory(
            produto="Produto Inativo",
            categoria=self.categoria,
            estoque=3,
            preco=29.90,
        )
        InventarioSaldo.objects.create(
            inventario=self.inventario_inativo,
            produto=self.produto_inativo,
            quantidade=3,
        )

    def test_home_exibe_apenas_produtos_de_inventarios_vitrine(self):
        """Testar que a home exibe apenas produtos de inventários com exibir_na_vitrine=True."""
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)

        # Verificar contexto
        produtos = response.context["my_products"]
        nomes_produtos = [p["produto"] for p in produtos]

        self.assertIn("Produto Vitrine", nomes_produtos)
        self.assertNotIn("Produto Oculto", nomes_produtos)
        self.assertNotIn("Produto Inativo", nomes_produtos)

    def test_home_nao_exibe_produtos_sem_saldo_em_vitrine(self):
        """Testar que produto sem saldo em inventário vitrine não aparece."""
        # Produto sem saldo em nenhum inventário vitrine
        produto_sem_saldo_vitrine = ProdutoFactory(
            produto="Produto Sem Vitrine",
            categoria=self.categoria,
            estoque=20,
            preco=199.90,
        )
        # Tem estoque no produto, mas não tem InventarioSaldo em inventário vitrine

        response = self.client.get(reverse("home"))
        produtos = response.context["my_products"]
        nomes_produtos = [p["produto"] for p in produtos]

        self.assertNotIn("Produto Sem Vitrine", nomes_produtos)

    def test_home_filtra_por_categoria_e_vitrine(self):
        """Testar que filtro de categoria também respeita filtro de vitrine."""
        outra_categoria = CategoriaFactory(categoria="Outra Categoria")

        # Produto em outra categoria, na vitrine
        produto_outra_cat = ProdutoFactory(
            produto="Produto Outra Categoria",
            categoria=outra_categoria,
            estoque=15,
            preco=149.90,
        )
        InventarioSaldo.objects.create(
            inventario=self.inventario_vitrine,
            produto=produto_outra_cat,
            quantidade=15,
        )

        # Filtrar pela categoria original
        response = self.client.get(reverse("home"), {"category": self.categoria.id})
        produtos = response.context["my_products"]
        nomes_produtos = [p["produto"] for p in produtos]

        self.assertIn("Produto Vitrine", nomes_produtos)
        self.assertNotIn("Produto Outra Categoria", nomes_produtos)
        self.assertNotIn("Produto Oculto", nomes_produtos)

    def test_home_produto_com_estoque_zero_nao_aparece(self):
        """Testar que produto com estoque zero não aparece mesmo em inventário vitrine."""
        produto_sem_estoque = ProdutoFactory(
            produto="Produto Sem Estoque",
            categoria=self.categoria,
            estoque=0,  # Estoque zero
            preco=79.90,
        )
        InventarioSaldo.objects.create(
            inventario=self.inventario_vitrine,
            produto=produto_sem_estoque,
            quantidade=0,  # Saldo zero no inventário
        )

        response = self.client.get(reverse("home"))
        produtos = response.context["my_products"]
        nomes_produtos = [p["produto"] for p in produtos]

        self.assertNotIn("Produto Sem Estoque", nomes_produtos)

    def test_home_htmx_request_retorna_partial(self):
        """Testar que requisição HTMX retorna template parcial."""
        response = self.client.get(
            reverse("home"),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(response.status_code, 200)
        # Verifica que é o template parcial (não tem estrutura completa de HTML)
        self.assertTemplateUsed(response, "pages/partials/product_list_partial.html")

    def test_home_busca_respeita_filtro_vitrine(self):
        """Testar que busca por texto também respeita filtro de vitrine."""
        response = self.client.get(reverse("home"), {"search": "Produto"})
        produtos = response.context["my_products"]
        nomes_produtos = [p["produto"] for p in produtos]

        # Deve encontrar apenas o produto na vitrine
        self.assertIn("Produto Vitrine", nomes_produtos)
        self.assertNotIn("Produto Oculto", nomes_produtos)


class HomeVitrineEdgeCasesTest(TestCase):
    """Testes de casos extremos para o filtro de vitrine."""

    def setUp(self):
        self.client = Client()

    def test_home_sem_inventarios_vitrine_retorna_lista_vazia(self):
        """Testar que home retorna lista vazia se não há inventários com vitrine."""
        categoria = CategoriaFactory()
        inventario = InventarioFactory(exibir_na_vitrine=False)

        produto = ProdutoFactory(
            produto="Produto Teste",
            categoria=categoria,
            estoque=10,
            preco=50.00,
        )
        InventarioSaldo.objects.create(
            inventario=inventario,
            produto=produto,
            quantidade=10,
        )

        response = self.client.get(reverse("home"))
        produtos = response.context["my_products"]

        self.assertEqual(len(produtos), 0)

    def test_home_produto_em_multiplos_inventarios(self):
        """Testar que produto em múltiplos inventários aparece se pelo menos um é vitrine."""
        categoria = CategoriaFactory()

        inv_vitrine = InventarioFactory(exibir_na_vitrine=True, is_ativo=True)
        inv_oculto = InventarioFactory(exibir_na_vitrine=False, is_ativo=True)

        produto = ProdutoFactory(
            produto="Produto Multi-Inventário",
            categoria=categoria,
            estoque=25,
            preco=100.00,
        )

        # Produto em ambos os inventários
        InventarioSaldo.objects.create(
            inventario=inv_vitrine,
            produto=produto,
            quantidade=15,
        )
        InventarioSaldo.objects.create(
            inventario=inv_oculto,
            produto=produto,
            quantidade=10,
        )

        response = self.client.get(reverse("home"))
        produtos = response.context["my_products"]
        nomes_produtos = [p["produto"] for p in produtos]

        # Deve aparecer porque tem saldo em inventário vitrine
        self.assertIn("Produto Multi-Inventário", nomes_produtos)
        # Deve aparecer apenas uma vez
        self.assertEqual(nomes_produtos.count("Produto Multi-Inventário"), 1)
