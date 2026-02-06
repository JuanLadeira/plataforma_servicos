import pytest
from django.test import Client
from django.test import TestCase
from django.urls import reverse

from plataforma_de_servicos.empresa.tests.factories import EmpresaFactory
from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.inventario.tests.factories import InventarioFactory
from plataforma_de_servicos.produto.tests.factories.atributos_factory import (
    AtributoFactory,
    ValorAtributoFactory,
    VariacaoProdutoFactory,
)
from plataforma_de_servicos.produto.tests.factories.categoria_factory import CategoriaFactory
from plataforma_de_servicos.produto.tests.factories.produto_factory import ProdutoFactory

pytestmark = pytest.mark.inventario


class HomeVitrineFilterTest(TestCase):
    """Testes para o filtro de variações por inventário na home."""

    def setUp(self):
        self.client = Client()

        # Empresa (tenant) para o teste
        self.empresa = EmpresaFactory(slug="loja-teste")
        self.tenant_host = "loja-teste.dominio.com"

        # Categoria deve ser criada antes do atributo
        self.categoria = CategoriaFactory(empresa=self.empresa)

        # Atributo e valor compartilhados
        self.atributo_cor = AtributoFactory(nome="Cor", categoria=self.categoria)
        self.valor_azul = ValorAtributoFactory(
            atributo=self.atributo_cor,
            valor="Azul",
        )

        # Inventário que deve aparecer na vitrine
        self.inventario_vitrine = InventarioFactory(
            nome="Loja Principal",
            is_ativo=True,
            exibir_na_vitrine=True,
            empresa=self.empresa,
        )

        # Inventário que NÃO deve aparecer na vitrine
        self.inventario_oculto = InventarioFactory(
            nome="Depósito Interno",
            is_ativo=True,
            exibir_na_vitrine=False,
            empresa=self.empresa,
        )

        # Inventário inativo (não deve aparecer)
        self.inventario_inativo = InventarioFactory(
            nome="Loja Fechada",
            is_ativo=False,
            exibir_na_vitrine=True,
            empresa=self.empresa,
        )

        # Produto na vitrine (tem saldo em inventário com exibir_na_vitrine=True)
        self.produto_vitrine = ProdutoFactory(
            produto="Produto Vitrine",
            categoria=self.categoria,
            estoque=10,
            preco=99.90,
            empresa=self.empresa,
            disponivel=True,
        )
        self.variacao_vitrine = VariacaoProdutoFactory(
            produto=self.produto_vitrine,
            estoque=10,
            valores=[self.valor_azul],
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
            empresa=self.empresa,
            disponivel=True,
        )
        self.variacao_oculto = VariacaoProdutoFactory(
            produto=self.produto_oculto,
            estoque=5,
            valores=[self.valor_azul],
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
            empresa=self.empresa,
            disponivel=True,
        )
        self.variacao_inativo = VariacaoProdutoFactory(
            produto=self.produto_inativo,
            estoque=3,
            valores=[self.valor_azul],
        )
        InventarioSaldo.objects.create(
            inventario=self.inventario_inativo,
            produto=self.produto_inativo,
            quantidade=3,
        )

    def _extrair_nomes_produtos(self, variacoes):
        """Extrai nomes dos produtos das variações."""
        # nome_completo é "Produto - Cor" ou similar
        # Extraímos apenas a parte do produto (antes do primeiro " - ")
        nomes = []
        for v in variacoes:
            nome = v.nome_completo.split(" - ")[0] if " - " in v.nome_completo else v.nome_completo
            nomes.append(nome)
        return nomes

    def test_home_exibe_apenas_produtos_de_inventarios_vitrine(self):
        """Testar que a home exibe apenas variações de inventários com exibir_na_vitrine=True."""
        response = self.client.get(reverse("home"), HTTP_HOST=self.tenant_host)

        self.assertEqual(response.status_code, 200)

        variacoes = response.context["my_variations"]
        nomes_produtos = self._extrair_nomes_produtos(variacoes)

        self.assertIn("Produto Vitrine", nomes_produtos)
        self.assertNotIn("Produto Oculto", nomes_produtos)
        self.assertNotIn("Produto Inativo", nomes_produtos)

    def test_home_nao_exibe_produtos_sem_saldo_em_vitrine(self):
        """Testar que produto sem saldo em inventário vitrine não aparece."""
        produto_sem_saldo_vitrine = ProdutoFactory(
            produto="Produto Sem Vitrine",
            categoria=self.categoria,
            estoque=20,
            preco=199.90,
            empresa=self.empresa,
            disponivel=True,
        )
        VariacaoProdutoFactory(
            produto=produto_sem_saldo_vitrine,
            estoque=20,
            valores=[self.valor_azul],
        )
        # Tem estoque na variação, mas não tem InventarioSaldo em inventário vitrine

        response = self.client.get(reverse("home"), HTTP_HOST=self.tenant_host)
        variacoes = response.context["my_variations"]
        nomes_produtos = self._extrair_nomes_produtos(variacoes)

        self.assertNotIn("Produto Sem Vitrine", nomes_produtos)

    def test_home_filtra_por_categoria_e_vitrine(self):
        """Testar que filtro de categoria também respeita filtro de vitrine."""
        outra_categoria = CategoriaFactory(categoria="Outra Categoria", empresa=self.empresa)

        produto_outra_cat = ProdutoFactory(
            produto="Produto Outra Categoria",
            categoria=outra_categoria,
            estoque=15,
            preco=149.90,
            empresa=self.empresa,
            disponivel=True,
        )
        VariacaoProdutoFactory(
            produto=produto_outra_cat,
            estoque=15,
            valores=[self.valor_azul],
        )
        InventarioSaldo.objects.create(
            inventario=self.inventario_vitrine,
            produto=produto_outra_cat,
            quantidade=15,
        )

        # Filtrar pela categoria original
        response = self.client.get(
            reverse("home"),
            {"category": self.categoria.id},
            HTTP_HOST=self.tenant_host,
        )
        variacoes = response.context["my_variations"]
        nomes_produtos = self._extrair_nomes_produtos(variacoes)

        self.assertIn("Produto Vitrine", nomes_produtos)
        self.assertNotIn("Produto Outra Categoria", nomes_produtos)
        self.assertNotIn("Produto Oculto", nomes_produtos)

    def test_home_produto_com_estoque_zero_nao_aparece(self):
        """Testar que variação com estoque zero não aparece mesmo em inventário vitrine."""
        produto_sem_estoque = ProdutoFactory(
            produto="Produto Sem Estoque",
            categoria=self.categoria,
            estoque=0,
            preco=79.90,
            empresa=self.empresa,
            disponivel=True,
        )
        VariacaoProdutoFactory(
            produto=produto_sem_estoque,
            estoque=0,  # Variação com estoque zero
            valores=[self.valor_azul],
        )
        InventarioSaldo.objects.create(
            inventario=self.inventario_vitrine,
            produto=produto_sem_estoque,
            quantidade=0,
        )

        response = self.client.get(reverse("home"), HTTP_HOST=self.tenant_host)
        variacoes = response.context["my_variations"]
        nomes_produtos = self._extrair_nomes_produtos(variacoes)

        self.assertNotIn("Produto Sem Estoque", nomes_produtos)

    def test_home_htmx_request_retorna_partial(self):
        """Testar que requisição HTMX retorna template parcial."""
        response = self.client.get(
            reverse("home"),
            HTTP_HX_REQUEST="true",
            HTTP_HOST=self.tenant_host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/partials/product_list_partial.html")

    def test_home_busca_respeita_filtro_vitrine(self):
        """Testar que busca por texto também respeita filtro de vitrine."""
        response = self.client.get(
            reverse("home"),
            {"search": "Produto"},
            HTTP_HOST=self.tenant_host,
        )
        variacoes = response.context["my_variations"]
        nomes_produtos = self._extrair_nomes_produtos(variacoes)

        # Deve encontrar apenas o produto na vitrine
        self.assertIn("Produto Vitrine", nomes_produtos)
        self.assertNotIn("Produto Oculto", nomes_produtos)


class HomeVitrineEdgeCasesTest(TestCase):
    """Testes de casos extremos para o filtro de vitrine."""

    def setUp(self):
        self.client = Client()
        self.empresa = EmpresaFactory(slug="loja-edge")
        self.tenant_host = "loja-edge.dominio.com"

        # Categoria é necessária para criar o atributo
        self.categoria = CategoriaFactory(empresa=self.empresa)
        self.atributo_cor = AtributoFactory(nome="Cor", categoria=self.categoria)
        self.valor_verde = ValorAtributoFactory(
            atributo=self.atributo_cor,
            valor="Verde",
        )

    def _extrair_nomes_produtos(self, variacoes):
        """Extrai nomes dos produtos das variações."""
        nomes = []
        for v in variacoes:
            nome = v.nome_completo.split(" - ")[0] if " - " in v.nome_completo else v.nome_completo
            nomes.append(nome)
        return nomes

    def test_home_sem_inventarios_vitrine_retorna_lista_vazia(self):
        """Testar que home retorna lista vazia se não há inventários com vitrine."""
        categoria = CategoriaFactory(empresa=self.empresa)
        inventario = InventarioFactory(exibir_na_vitrine=False, empresa=self.empresa)

        produto = ProdutoFactory(
            produto="Produto Teste",
            categoria=categoria,
            estoque=10,
            preco=50.00,
            empresa=self.empresa,
            disponivel=True,
        )
        VariacaoProdutoFactory(
            produto=produto,
            estoque=10,
            valores=[self.valor_verde],
        )
        InventarioSaldo.objects.create(
            inventario=inventario,
            produto=produto,
            quantidade=10,
        )

        response = self.client.get(reverse("home"), HTTP_HOST=self.tenant_host)
        variacoes = response.context["my_variations"]

        self.assertEqual(len(variacoes), 0)

    def test_home_produto_em_multiplos_inventarios(self):
        """Testar que variação em múltiplos inventários aparece se pelo menos um é vitrine."""
        categoria = CategoriaFactory(empresa=self.empresa)

        inv_vitrine = InventarioFactory(
            exibir_na_vitrine=True,
            is_ativo=True,
            empresa=self.empresa,
        )
        inv_oculto = InventarioFactory(
            exibir_na_vitrine=False,
            is_ativo=True,
            empresa=self.empresa,
        )

        produto = ProdutoFactory(
            produto="Produto Multi-Inventario",
            categoria=categoria,
            estoque=25,
            preco=100.00,
            empresa=self.empresa,
            disponivel=True,
        )
        VariacaoProdutoFactory(
            produto=produto,
            estoque=25,
            valores=[self.valor_verde],
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

        response = self.client.get(reverse("home"), HTTP_HOST=self.tenant_host)
        variacoes = response.context["my_variations"]
        nomes_produtos = self._extrair_nomes_produtos(variacoes)

        # Deve aparecer porque tem saldo em inventário vitrine
        self.assertIn("Produto Multi-Inventario", nomes_produtos)
        # Deve aparecer apenas uma vez
        self.assertEqual(nomes_produtos.count("Produto Multi-Inventario"), 1)

    def test_home_sem_tenant_retorna_lista_vazia(self):
        """Testar que home sem tenant retorna lista vazia."""
        categoria = CategoriaFactory(empresa=self.empresa)
        inventario = InventarioFactory(
            exibir_na_vitrine=True,
            is_ativo=True,
            empresa=self.empresa,
        )
        produto = ProdutoFactory(
            produto="Produto Qualquer",
            categoria=categoria,
            estoque=10,
            preco=50.00,
            empresa=self.empresa,
            disponivel=True,
        )
        VariacaoProdutoFactory(
            produto=produto,
            estoque=10,
            valores=[self.valor_verde],
        )
        InventarioSaldo.objects.create(
            inventario=inventario,
            produto=produto,
            quantidade=10,
        )

        # Requisição sem subdomínio válido (sem tenant)
        response = self.client.get(reverse("home"), HTTP_HOST="localhost")
        variacoes = response.context["my_variations"]

        self.assertEqual(len(variacoes), 0)

    def test_isolamento_entre_empresas(self):
        """Testar que dados de uma empresa não aparecem na outra."""
        outra_empresa = EmpresaFactory(slug="outra-loja")
        outra_host = "outra-loja.dominio.com"

        categoria = CategoriaFactory(empresa=self.empresa)
        inventario = InventarioFactory(
            exibir_na_vitrine=True,
            is_ativo=True,
            empresa=self.empresa,
        )
        produto = ProdutoFactory(
            produto="Produto Empresa Original",
            categoria=categoria,
            estoque=10,
            preco=50.00,
            empresa=self.empresa,
            disponivel=True,
        )
        VariacaoProdutoFactory(
            produto=produto,
            estoque=10,
            valores=[self.valor_verde],
        )
        InventarioSaldo.objects.create(
            inventario=inventario,
            produto=produto,
            quantidade=10,
        )

        # Acessar da outra empresa deve retornar lista vazia
        response = self.client.get(reverse("home"), HTTP_HOST=outra_host)
        variacoes = response.context["my_variations"]

        self.assertEqual(len(variacoes), 0)
