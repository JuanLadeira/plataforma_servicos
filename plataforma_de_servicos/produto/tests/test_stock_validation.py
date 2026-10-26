import pytest

from plataforma_de_servicos.produto.admin.gerente_admin import ProdutoGerenteAdmin
from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.produto.models import VariacaoProduto
from plataforma_de_servicos.produto.tests.factories import AtributoFactory
from plataforma_de_servicos.produto.tests.factories import ProdutoFactory
from plataforma_de_servicos.produto.tests.factories import ValorAtributoFactory
from plataforma_de_servicos.produto.tests.factories import VariacaoProdutoFactory


@pytest.fixture
def produto_com_estoque(db):
    """Cria um produto com estoque definido."""
    produto = ProdutoFactory(estoque=10)
    return produto


@pytest.fixture
def atributo_tamanho(db, produto_com_estoque):
    """Cria atributo Tamanho com valores, usando a mesma categoria do produto."""
    # Atributo deve usar a mesma categoria do produto
    atributo = AtributoFactory(nome="Tamanho", categoria=produto_com_estoque.categoria)
    ValorAtributoFactory(atributo=atributo, valor="Pequeno")
    ValorAtributoFactory(atributo=atributo, valor="Grande")
    return atributo


class TestProdutoGerenteAdminEstoqueDisplay:
    """Testes para os métodos de exibição de estoque no admin."""

    @pytest.fixture
    def admin_instance(self, db):
        """Retorna uma instância do ProdutoGerenteAdmin."""
        from django.contrib.admin.sites import AdminSite
        return ProdutoGerenteAdmin(Produto, AdminSite())

    def test_estoque_display_com_estoque(self, admin_instance, produto_com_estoque):
        """Deve mostrar o estoque total do produto."""
        result = admin_instance.estoque_display(produto_com_estoque)
        assert result == "10"

    def test_estoque_display_sem_estoque(self, admin_instance, db):
        """Produto sem saldo em depósito mostra 0."""
        produto = ProdutoFactory()
        assert admin_instance.estoque_display(produto) == "0"

    def test_estoque_display_produto_novo(self, admin_instance, db):
        """Deve retornar '-' para produto não salvo."""
        produto = Produto(produto="Novo Produto")
        result = admin_instance.estoque_display(produto)
        assert result == "-"

    def test_estoque_variacoes_display(
        self, admin_instance, produto_com_estoque, atributo_tamanho,
    ):
        """Deve mostrar a soma do estoque das variações."""
        produto = produto_com_estoque
        var1 = VariacaoProdutoFactory(
            produto=produto, estoque=3, valores=[atributo_tamanho.valores.get(valor="Pequeno")],
        )
        VariacaoProdutoFactory(produto=produto, estoque=4, valores=[atributo_tamanho.valores.get(valor="Grande")])
        assert admin_instance.estoque_variacoes_display(produto) == "7"
        var1.produto.refresh_from_db()
        assert admin_instance.estoque_display(var1.produto) == "17"  # 10 sem variação + 3 + 4

    def test_estoque_variacoes_display_sem_variacoes(
        self, admin_instance, produto_com_estoque,
    ):
        """Deve mostrar '0' quando não há variações."""
        result = admin_instance.estoque_variacoes_display(produto_com_estoque)
        assert result == "0"


class TestFormsetSemRegraDeSomaDeEstoque:
    """Com o estoque derivado dos depósitos (issue #144), o formset não compara variações com o produto."""

    def test_formset_valido_com_variacoes_acima_do_saldo_sem_variacao(self, produto_com_estoque, atributo_tamanho):
        from django.forms.models import inlineformset_factory

        from plataforma_de_servicos.produto.admin.gerente_admin import VariacaoProdutoInlineFormSet

        VariacaoProdutoFactory(
            produto=produto_com_estoque, estoque=50, valores=[atributo_tamanho.valores.get(valor="Pequeno")],
        )
        FormSet = inlineformset_factory(
            Produto, VariacaoProduto, formset=VariacaoProdutoInlineFormSet, fields=["valores"], extra=0,
        )
        variacao = produto_com_estoque.variacoes.get()
        data = {
            "variacoes-TOTAL_FORMS": "1",
            "variacoes-INITIAL_FORMS": "1",
            "variacoes-0-id": str(variacao.pk),
            "variacoes-0-produto": str(produto_com_estoque.pk),
            "variacoes-0-valores": [str(v.pk) for v in variacao.valores.all()],
        }
        formset = FormSet(data, instance=produto_com_estoque)
        assert formset.is_valid(), formset.errors


class TestVariacaoAtributoSelecaoUnica:
    """Testes para validação de seleção única em atributos."""

    @pytest.fixture
    def produto(self, db):
        """Cria um produto."""
        return ProdutoFactory()

    @pytest.fixture
    def atributo_cor_selecao_unica(self, produto):
        """Cria atributo Cor que permite apenas uma seleção."""
        atributo = AtributoFactory(
            nome="Cor",
            categoria=produto.categoria,
            multipla_selecao=False,
        )
        ValorAtributoFactory(atributo=atributo, valor="Vermelho")
        ValorAtributoFactory(atributo=atributo, valor="Azul")
        ValorAtributoFactory(atributo=atributo, valor="Verde")
        return atributo

    @pytest.fixture
    def atributo_extras_multipla_selecao(self, produto):
        """Cria atributo Extras que permite múltipla seleção."""
        atributo = AtributoFactory(
            nome="Extras",
            categoria=produto.categoria,
            multipla_selecao=True,
        )
        ValorAtributoFactory(atributo=atributo, valor="Embalagem")
        ValorAtributoFactory(atributo=atributo, valor="Cartão")
        return atributo

    def test_variacao_com_um_valor_selecao_unica_valido(
        self, produto, atributo_cor_selecao_unica,
    ):
        """Variação com apenas um valor de atributo de seleção única é válido."""
        valor_vermelho = atributo_cor_selecao_unica.valores.get(valor="Vermelho")

        variacao = VariacaoProduto.objects.create(produto=produto)
        variacao.valores.add(valor_vermelho)

        # Verificar que só tem um valor do atributo
        valores_cor = [v for v in variacao.valores.all() if v.atributo == atributo_cor_selecao_unica]
        assert len(valores_cor) == 1

    def test_variacao_com_multiplos_valores_multipla_selecao_valido(
        self, produto, atributo_extras_multipla_selecao,
    ):
        """Variação com múltiplos valores de atributo de múltipla seleção é válido."""
        valor_embalagem = atributo_extras_multipla_selecao.valores.get(valor="Embalagem")
        valor_cartao = atributo_extras_multipla_selecao.valores.get(valor="Cartão")

        variacao = VariacaoProduto.objects.create(produto=produto)
        variacao.valores.add(valor_embalagem, valor_cartao)

        # Verificar que tem dois valores
        valores_extras = [v for v in variacao.valores.all() if v.atributo == atributo_extras_multipla_selecao]
        assert len(valores_extras) == 2

    def test_validacao_formset_selecao_unica_rejeita_multiplos_valores(
        self, produto, atributo_cor_selecao_unica,
    ):
        """Formset deve rejeitar múltiplos valores de atributo de seleção única."""
        from django import forms
        from django.forms.models import inlineformset_factory
        from plataforma_de_servicos.produto.admin.gerente_admin import VariacaoProdutoInlineFormSet

        valor_vermelho = atributo_cor_selecao_unica.valores.get(valor="Vermelho")
        valor_azul = atributo_cor_selecao_unica.valores.get(valor="Azul")

        # Criar formset usando factory
        FormSet = inlineformset_factory(
            Produto,
            VariacaoProduto,
            formset=VariacaoProdutoInlineFormSet,
            fields=["valores", "estoque"],
            extra=0,
        )
        formset = FormSet(instance=produto)

        # Testar a validação diretamente
        erros = []
        try:
            formset._validar_selecao_atributos([valor_vermelho, valor_azul], None)
        except forms.ValidationError as e:
            erros = e.messages

        assert len(erros) > 0
        assert "Cor" in erros[0]
        assert "apenas uma seleção" in erros[0]

    def test_validacao_formset_aceita_valores_de_atributos_diferentes(
        self, produto, atributo_cor_selecao_unica, atributo_extras_multipla_selecao,
    ):
        """Formset deve aceitar valores de atributos diferentes."""
        from django import forms
        from django.forms.models import inlineformset_factory
        from plataforma_de_servicos.produto.admin.gerente_admin import VariacaoProdutoInlineFormSet

        valor_vermelho = atributo_cor_selecao_unica.valores.get(valor="Vermelho")
        valor_embalagem = atributo_extras_multipla_selecao.valores.get(valor="Embalagem")
        valor_cartao = atributo_extras_multipla_selecao.valores.get(valor="Cartão")

        # Criar formset usando factory
        FormSet = inlineformset_factory(
            Produto,
            VariacaoProduto,
            formset=VariacaoProdutoInlineFormSet,
            fields=["valores", "estoque"],
            extra=0,
        )
        formset = FormSet(instance=produto)

        # Deve aceitar: 1 valor de Cor + 2 valores de Extras
        erros = []
        try:
            formset._validar_selecao_atributos(
                [valor_vermelho, valor_embalagem, valor_cartao],
                None,
            )
        except forms.ValidationError as e:
            erros = e.messages

        assert len(erros) == 0
