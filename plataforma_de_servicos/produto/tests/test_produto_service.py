"""
Testes unitários para o ProdutoService.
"""

from decimal import Decimal

import pytest

from plataforma_de_servicos.empresa.tests.factories import EmpresaFactory
from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.inventario.tests.factories import InventarioFactory
from plataforma_de_servicos.produto.services import ProdutoService
from plataforma_de_servicos.produto.services.produto_service import (
    ProdutoVitrine,
    VariacaoPrecoResult,
)
from plataforma_de_servicos.produto.tests.factories import (
    AtributoFactory,
    CategoriaFactory,
    ProdutoFactory,
    ValorAtributoFactory,
    VariacaoProdutoFactory,
)

pytestmark = [pytest.mark.django_db, pytest.mark.produto]


class TestProdutoServiceListarProdutosVitrine:
    """Testes para o método listar_produtos_vitrine."""

    def test_retorna_produtos_de_inventario_vitrine(self):
        """Deve retornar apenas produtos em inventários com exibir_na_vitrine=True."""
        empresa = EmpresaFactory()
        categoria = CategoriaFactory(empresa=empresa)
        inventario_vitrine = InventarioFactory(
            is_ativo=True,
            exibir_na_vitrine=True,
            empresa=empresa,
        )

        produto = ProdutoFactory(
            categoria=categoria,
            estoque=10,
            preco=Decimal("99.90"),
            empresa=empresa,
        )
        InventarioSaldo.objects.create(
            inventario=inventario_vitrine,
            produto=produto,
            quantidade=10,
        )

        produtos, categoria_result = ProdutoService.listar_produtos_vitrine(empresa=empresa)

        assert produtos.count() == 1
        assert produtos.first().id == produto.id
        assert categoria_result == "Todos os produtos"

    def test_nao_retorna_produtos_de_inventario_oculto(self):
        """Não deve retornar produtos em inventários com exibir_na_vitrine=False."""
        empresa = EmpresaFactory()
        categoria = CategoriaFactory(empresa=empresa)
        inventario_oculto = InventarioFactory(
            is_ativo=True,
            exibir_na_vitrine=False,
            empresa=empresa,
        )

        produto = ProdutoFactory(
            categoria=categoria,
            estoque=10,
            preco=Decimal("99.90"),
            empresa=empresa,
        )
        InventarioSaldo.objects.create(
            inventario=inventario_oculto,
            produto=produto,
            quantidade=10,
        )

        produtos, _ = ProdutoService.listar_produtos_vitrine(empresa=empresa)

        assert produtos.count() == 0

    def test_nao_retorna_produtos_de_inventario_inativo(self):
        """Não deve retornar produtos em inventários inativos."""
        empresa = EmpresaFactory()
        categoria = CategoriaFactory(empresa=empresa)
        inventario_inativo = InventarioFactory(
            is_ativo=False,
            exibir_na_vitrine=True,
            empresa=empresa,
        )

        produto = ProdutoFactory(
            categoria=categoria,
            estoque=10,
            preco=Decimal("99.90"),
            empresa=empresa,
        )
        InventarioSaldo.objects.create(
            inventario=inventario_inativo,
            produto=produto,
            quantidade=10,
        )

        produtos, _ = ProdutoService.listar_produtos_vitrine(empresa=empresa)

        assert produtos.count() == 0

    def test_filtra_por_categoria(self):
        """Deve filtrar produtos pela categoria especificada."""
        empresa = EmpresaFactory()
        categoria1 = CategoriaFactory(categoria="Categoria 1", empresa=empresa)
        categoria2 = CategoriaFactory(categoria="Categoria 2", empresa=empresa)
        inventario = InventarioFactory(is_ativo=True, exibir_na_vitrine=True, empresa=empresa)

        produto1 = ProdutoFactory(categoria=categoria1, estoque=10, preco=Decimal("50.00"), empresa=empresa)
        produto2 = ProdutoFactory(categoria=categoria2, estoque=10, preco=Decimal("60.00"), empresa=empresa)

        InventarioSaldo.objects.create(inventario=inventario, produto=produto1, quantidade=10)
        InventarioSaldo.objects.create(inventario=inventario, produto=produto2, quantidade=10)

        produtos, categoria_result = ProdutoService.listar_produtos_vitrine(
            category_id=str(categoria1.id),
            empresa=empresa,
        )

        assert produtos.count() == 1
        assert produtos.first().id == produto1.id
        assert categoria_result == categoria1

    def test_filtra_por_busca(self):
        """Deve filtrar produtos pelo texto de busca."""
        empresa = EmpresaFactory()
        categoria = CategoriaFactory(empresa=empresa)
        inventario = InventarioFactory(is_ativo=True, exibir_na_vitrine=True, empresa=empresa)

        produto1 = ProdutoFactory(
            produto="Pizza Margherita Especial",
            categoria=categoria,
            estoque=10,
            preco=Decimal("50.00"),
            empresa=empresa,
        )
        produto2 = ProdutoFactory(
            produto="Refrigerante Cola",
            categoria=categoria,
            estoque=10,
            preco=Decimal("10.00"),
            empresa=empresa,
        )

        InventarioSaldo.objects.create(inventario=inventario, produto=produto1, quantidade=10)
        InventarioSaldo.objects.create(inventario=inventario, produto=produto2, quantidade=10)

        produtos, _ = ProdutoService.listar_produtos_vitrine(search="Pizza", empresa=empresa)

        assert produtos.count() == 1
        assert produtos.first().id == produto1.id

    def test_category_id_invalido_retorna_todos_produtos(self):
        """Com category_id inválido, deve retornar todos os produtos."""
        empresa = EmpresaFactory()
        categoria = CategoriaFactory(empresa=empresa)
        inventario = InventarioFactory(is_ativo=True, exibir_na_vitrine=True, empresa=empresa)

        produto = ProdutoFactory(categoria=categoria, estoque=10, preco=Decimal("50.00"), empresa=empresa)
        InventarioSaldo.objects.create(inventario=inventario, produto=produto, quantidade=10)

        produtos, categoria_result = ProdutoService.listar_produtos_vitrine(
            category_id="invalid",
            empresa=empresa,
        )

        assert produtos.count() == 1
        assert categoria_result == "Todos os produtos"

    def test_sem_empresa_retorna_lista_vazia(self):
        """Sem empresa, deve retornar lista vazia (isolamento multitenancy)."""
        produtos, categoria_result = ProdutoService.listar_produtos_vitrine(empresa=None)

        assert produtos.count() == 0
        assert categoria_result == "Todos os produtos"


class TestProdutoServicePrepararProdutosParaVitrine:
    """Testes para o método preparar_produtos_para_vitrine."""

    def test_retorna_lista_de_produto_vitrine(self):
        """Deve retornar lista de ProdutoVitrine com dados corretos."""
        empresa = EmpresaFactory()
        categoria = CategoriaFactory(categoria="Pizzas", empresa=empresa)
        inventario = InventarioFactory(is_ativo=True, exibir_na_vitrine=True, empresa=empresa)

        produto = ProdutoFactory(
            produto="Pizza Teste",
            categoria=categoria,
            estoque=10,
            preco=Decimal("49.90"),
            empresa=empresa,
        )
        InventarioSaldo.objects.create(inventario=inventario, produto=produto, quantidade=10)

        produtos_qs, _ = ProdutoService.listar_produtos_vitrine(empresa=empresa)
        resultado = ProdutoService.preparar_produtos_para_vitrine(produtos_qs)

        assert len(resultado) == 1
        assert isinstance(resultado[0], ProdutoVitrine)
        assert resultado[0].produto == "Pizza Teste"
        assert resultado[0].categoria == "Pizzas"
        assert resultado[0].preco == Decimal("49.90")
        assert resultado[0].estoque == 10

    def test_exclui_produtos_com_estoque_zero(self):
        """Não deve incluir produtos com estoque zero."""
        empresa = EmpresaFactory()
        categoria = CategoriaFactory(empresa=empresa)
        inventario = InventarioFactory(is_ativo=True, exibir_na_vitrine=True, empresa=empresa)

        produto = ProdutoFactory(
            categoria=categoria,
            estoque=0,
            preco=Decimal("49.90"),
            empresa=empresa,
        )
        InventarioSaldo.objects.create(inventario=inventario, produto=produto, quantidade=5)

        produtos_qs, _ = ProdutoService.listar_produtos_vitrine(empresa=empresa)
        resultado = ProdutoService.preparar_produtos_para_vitrine(produtos_qs)

        assert len(resultado) == 0

    def test_produto_sem_categoria_retorna_sem_categoria(self):
        """Produto sem categoria deve retornar 'Sem categoria'."""
        empresa = EmpresaFactory()
        inventario = InventarioFactory(is_ativo=True, exibir_na_vitrine=True, empresa=empresa)

        produto = ProdutoFactory(
            categoria=None,
            estoque=10,
            preco=Decimal("49.90"),
            empresa=empresa,
        )
        InventarioSaldo.objects.create(inventario=inventario, produto=produto, quantidade=10)

        produtos_qs, _ = ProdutoService.listar_produtos_vitrine(empresa=empresa)
        resultado = ProdutoService.preparar_produtos_para_vitrine(produtos_qs)

        assert len(resultado) == 1
        assert resultado[0].categoria == "Sem categoria"


class TestProdutoServiceObterAtributosVariacoes:
    """Testes para o método obter_atributos_variacoes."""

    def test_retorna_atributos_unicos(self):
        """Deve retornar atributos únicos das variações."""
        produto = ProdutoFactory(preco=Decimal("100.00"))

        # Atributos devem usar a mesma categoria do produto
        cor_attr = AtributoFactory(nome="Cor", categoria=produto.categoria)
        tam_attr = AtributoFactory(nome="Tamanho", categoria=produto.categoria)

        cor_vermelho = ValorAtributoFactory(atributo=cor_attr, valor="Vermelho")
        cor_azul = ValorAtributoFactory(atributo=cor_attr, valor="Azul")
        tam_p = ValorAtributoFactory(atributo=tam_attr, valor="P")
        tam_m = ValorAtributoFactory(atributo=tam_attr, valor="M")

        VariacaoProdutoFactory(produto=produto, valores=[cor_vermelho, tam_p])
        VariacaoProdutoFactory(produto=produto, valores=[cor_azul, tam_m])

        atributos = ProdutoService.obter_atributos_variacoes(produto)

        assert len(atributos) == 2

        nomes_atributos = [a["atributo"].nome for a in atributos]
        assert "Cor" in nomes_atributos
        assert "Tamanho" in nomes_atributos

    def test_valores_ordenados_alfabeticamente(self):
        """Valores de cada atributo devem estar ordenados alfabeticamente."""
        produto = ProdutoFactory(preco=Decimal("100.00"))

        # Atributo deve usar a mesma categoria do produto
        cor_attr = AtributoFactory(nome="Cor", categoria=produto.categoria)
        cor_z = ValorAtributoFactory(atributo=cor_attr, valor="Zebra")
        cor_a = ValorAtributoFactory(atributo=cor_attr, valor="Amarelo")
        cor_m = ValorAtributoFactory(atributo=cor_attr, valor="Marrom")

        VariacaoProdutoFactory(produto=produto, valores=[cor_z])
        VariacaoProdutoFactory(produto=produto, valores=[cor_a])
        VariacaoProdutoFactory(produto=produto, valores=[cor_m])

        atributos = ProdutoService.obter_atributos_variacoes(produto)

        valores = atributos[0]["valores"]
        valores_texto = [v.valor for v in valores]
        assert valores_texto == ["Amarelo", "Marrom", "Zebra"]

    def test_produto_sem_variacoes_retorna_lista_vazia(self):
        """Produto sem variações deve retornar lista vazia."""
        produto = ProdutoFactory(preco=Decimal("100.00"))

        atributos = ProdutoService.obter_atributos_variacoes(produto)

        assert atributos == []


class TestProdutoServiceCalcularPrecoVariacao:
    """Testes para o método calcular_preco_variacao."""

    def test_sem_valores_retorna_preco_base(self):
        """Sem valores selecionados, deve retornar preço base do produto."""
        produto = ProdutoFactory(preco=Decimal("100.00"), estoque=10)

        resultado = ProdutoService.calcular_preco_variacao(produto, None)

        assert isinstance(resultado, VariacaoPrecoResult)
        assert resultado.preco == "100.00"
        assert resultado.preco_formatado == "R$ 100,00"
        assert resultado.estoque == 10
        assert resultado.variation_id is None
        assert resultado.disponivel is True

    def test_com_variacao_encontrada_retorna_preco_variacao(self):
        """Com variação encontrada, deve retornar preço calculado."""
        produto = ProdutoFactory(preco=Decimal("100.00"), estoque=10)

        # Atributo deve usar a mesma categoria do produto
        cor_attr = AtributoFactory(nome="Cor", categoria=produto.categoria)
        cor_valor = ValorAtributoFactory(
            atributo=cor_attr,
            valor="Premium",
            preco_adicional=Decimal("25.00"),
        )

        variacao = VariacaoProdutoFactory(
            produto=produto,
            preco=Decimal("100.00"),
            estoque=5,
            valores=[cor_valor],
        )

        resultado = ProdutoService.calcular_preco_variacao(
            produto,
            [str(cor_valor.id)],
        )

        assert resultado.preco == "125.00"
        assert resultado.preco_formatado == "R$ 125,00"
        assert resultado.estoque == 5
        assert resultado.variation_id == variacao.id
        assert resultado.disponivel is True

    def test_variacao_sem_estoque_retorna_indisponivel(self):
        """Variação sem estoque deve retornar disponivel=False."""
        produto = ProdutoFactory(preco=Decimal("100.00"), estoque=10)

        # Atributo deve usar a mesma categoria do produto
        cor_attr = AtributoFactory(nome="Cor", categoria=produto.categoria)
        cor_valor = ValorAtributoFactory(atributo=cor_attr, valor="Normal")

        VariacaoProdutoFactory(
            produto=produto,
            preco=Decimal("100.00"),
            estoque=0,
            valores=[cor_valor],
        )

        resultado = ProdutoService.calcular_preco_variacao(
            produto,
            [str(cor_valor.id)],
        )

        assert resultado.disponivel is False

    def test_combinacao_invalida_retorna_preco_base(self):
        """Combinação inválida deve retornar preço base com flag combinacao_invalida."""
        produto = ProdutoFactory(preco=Decimal("100.00"), estoque=10)

        # Atributo deve usar a mesma categoria do produto
        cor_attr = AtributoFactory(nome="Cor", categoria=produto.categoria)
        cor_valor = ValorAtributoFactory(atributo=cor_attr, valor="Normal")

        # Não cria variação com esse valor

        resultado = ProdutoService.calcular_preco_variacao(
            produto,
            [str(cor_valor.id)],
        )

        assert resultado.preco == "100.00"
        assert resultado.combinacao_invalida is True

    def test_produto_sem_preco_retorna_zero(self):
        """Produto sem preço deve retornar '0' e R$ 0,00."""
        produto = ProdutoFactory(preco=None, estoque=0)

        resultado = ProdutoService.calcular_preco_variacao(produto, None)

        assert resultado.preco == "0"
        assert resultado.preco_formatado == "R$ 0,00"
        assert resultado.disponivel is False


class TestProdutoServiceBuscarVariacaoPorValores:
    """Testes para o método buscar_variacao_por_valores."""

    def test_encontra_variacao_com_valores_exatos(self):
        """Deve encontrar variação que corresponde exatamente aos valores."""
        produto = ProdutoFactory(preco=Decimal("100.00"))

        # Atributos devem usar a mesma categoria do produto
        cor_attr = AtributoFactory(nome="Cor", categoria=produto.categoria)
        tam_attr = AtributoFactory(nome="Tamanho", categoria=produto.categoria)

        cor_valor = ValorAtributoFactory(atributo=cor_attr, valor="Azul")
        tam_valor = ValorAtributoFactory(atributo=tam_attr, valor="M")

        variacao = VariacaoProdutoFactory(
            produto=produto,
            valores=[cor_valor, tam_valor],
        )

        resultado = ProdutoService.buscar_variacao_por_valores(
            produto,
            [str(cor_valor.id), str(tam_valor.id)],
        )

        assert resultado is not None
        assert resultado.id == variacao.id

    def test_nao_encontra_variacao_com_valores_parciais(self):
        """Não deve encontrar variação com apenas parte dos valores."""
        produto = ProdutoFactory(preco=Decimal("100.00"))

        # Atributos devem usar a mesma categoria do produto
        cor_attr = AtributoFactory(nome="Cor", categoria=produto.categoria)
        tam_attr = AtributoFactory(nome="Tamanho", categoria=produto.categoria)

        cor_valor = ValorAtributoFactory(atributo=cor_attr, valor="Azul")
        tam_valor = ValorAtributoFactory(atributo=tam_attr, valor="M")

        VariacaoProdutoFactory(
            produto=produto,
            valores=[cor_valor, tam_valor],
        )

        # Busca apenas com cor, sem tamanho
        resultado = ProdutoService.buscar_variacao_por_valores(
            produto,
            [str(cor_valor.id)],
        )

        assert resultado is None

    def test_nao_encontra_variacao_inexistente(self):
        """Não deve encontrar variação para valores que não existem combinados."""
        produto = ProdutoFactory(preco=Decimal("100.00"))

        # Atributo deve usar a mesma categoria do produto
        cor_attr = AtributoFactory(nome="Cor", categoria=produto.categoria)
        cor_vermelho = ValorAtributoFactory(atributo=cor_attr, valor="Vermelho")
        cor_azul = ValorAtributoFactory(atributo=cor_attr, valor="Azul")

        # Cria variação apenas com vermelho
        VariacaoProdutoFactory(produto=produto, valores=[cor_vermelho])

        # Busca com azul
        resultado = ProdutoService.buscar_variacao_por_valores(
            produto,
            [str(cor_azul.id)],
        )

        assert resultado is None


class TestProdutoServiceFormatarPrecoBr:
    """Testes para o método _formatar_preco_br."""

    def test_formata_preco_corretamente(self):
        """Deve formatar preço no padrão brasileiro."""
        preco = Decimal("1234.56")

        resultado = ProdutoService._formatar_preco_br(preco)

        assert resultado == "R$ 1.234,56"

    def test_formata_preco_none_como_zero(self):
        """Deve formatar None como R$ 0,00."""
        resultado = ProdutoService._formatar_preco_br(None)

        assert resultado == "R$ 0,00"

    def test_formata_preco_grande(self):
        """Deve formatar preços grandes corretamente."""
        preco = Decimal("1234567.89")

        resultado = ProdutoService._formatar_preco_br(preco)

        assert resultado == "R$ 1.234.567,89"

    def test_formata_preco_pequeno(self):
        """Deve formatar preços pequenos corretamente."""
        preco = Decimal("0.99")

        resultado = ProdutoService._formatar_preco_br(preco)

        assert resultado == "R$ 0,99"
