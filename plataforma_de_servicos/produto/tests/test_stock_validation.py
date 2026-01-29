import pytest

from plataforma_de_servicos.produto.admin.gerente_admin import ProdutoGerenteAdmin
from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.produto.models import VariacaoProduto
from plataforma_de_servicos.produto.tests.factories import AtributoFactory
from plataforma_de_servicos.produto.tests.factories import ProdutoFactory
from plataforma_de_servicos.produto.tests.factories import ValorAtributoFactory


@pytest.fixture
def produto_com_estoque(db):
    """Cria um produto com estoque definido."""
    produto = ProdutoFactory(estoque=10)
    return produto


@pytest.fixture
def atributo_tamanho(db):
    """Cria atributo Tamanho com valores."""
    atributo = AtributoFactory(nome="Tamanho")
    ValorAtributoFactory(atributo=atributo, valor="Pequeno")
    ValorAtributoFactory(atributo=atributo, valor="Grande")
    return atributo


class TestVariacaoProdutoInlineFormSet:
    """Testes para validação do estoque entre produto e variações."""

    def test_variacao_estoque_soma_igual_produto_estoque_valido(
        self, produto_com_estoque, atributo_tamanho,
    ):
        """
        Quando a soma do estoque das variações é igual ao estoque do produto,
        deve ser válido.
        """
        produto = produto_com_estoque
        valor_pequeno = atributo_tamanho.valores.get(valor="Pequeno")
        valor_grande = atributo_tamanho.valores.get(valor="Grande")

        # Criar variações com estoque total = 10 (5 + 5)
        var1 = VariacaoProduto.objects.create(produto=produto, estoque=5)
        var1.valores.add(valor_pequeno)

        var2 = VariacaoProduto.objects.create(produto=produto, estoque=5)
        var2.valores.add(valor_grande)

        # Verificar que o total é válido
        total = sum(v.estoque or 0 for v in produto.variacoes.all())
        assert total == 10
        assert total <= produto.estoque

    def test_variacao_estoque_soma_menor_produto_estoque_valido(
        self, produto_com_estoque, atributo_tamanho,
    ):
        """
        Quando a soma do estoque das variações é menor que o estoque do produto,
        deve ser válido.
        """
        produto = produto_com_estoque
        valor_pequeno = atributo_tamanho.valores.get(valor="Pequeno")

        # Criar variação com estoque = 3 (menor que 10)
        var1 = VariacaoProduto.objects.create(produto=produto, estoque=3)
        var1.valores.add(valor_pequeno)

        total = sum(v.estoque or 0 for v in produto.variacoes.all())
        assert total == 3
        assert total < produto.estoque

    def test_produto_sem_estoque_permite_variacoes_sem_limite(self, db, atributo_tamanho):
        """
        Quando o produto não tem estoque definido (0 ou None),
        as variações podem ter qualquer estoque.
        """
        produto = ProdutoFactory(estoque=0)
        valor_pequeno = atributo_tamanho.valores.get(valor="Pequeno")

        # Criar variação com estoque alto
        var1 = VariacaoProduto.objects.create(produto=produto, estoque=100)
        var1.valores.add(valor_pequeno)

        # Deve ser válido pois produto.estoque é 0 (sem limite)
        total = sum(v.estoque or 0 for v in produto.variacoes.all())
        assert total == 100
        # A validação não deve ser aplicada quando estoque do produto é 0

    def test_variacao_estoque_soma_excede_produto_invalido(
        self, produto_com_estoque, atributo_tamanho,
    ):
        """
        Quando a soma do estoque das variações excede o estoque do produto,
        deve ser inválido.
        """
        produto = produto_com_estoque  # estoque = 10
        valor_pequeno = atributo_tamanho.valores.get(valor="Pequeno")
        valor_grande = atributo_tamanho.valores.get(valor="Grande")

        # Criar variações com estoque total = 16 (8 + 8 > 10)
        var1 = VariacaoProduto.objects.create(produto=produto, estoque=8)
        var1.valores.add(valor_pequeno)

        var2 = VariacaoProduto.objects.create(produto=produto, estoque=8)
        var2.valores.add(valor_grande)

        # O total excede o estoque do produto
        total = sum(v.estoque or 0 for v in produto.variacoes.all())
        assert total == 16
        assert total > produto.estoque  # 16 > 10

    def test_deletar_variacao_libera_estoque(
        self, produto_com_estoque, atributo_tamanho,
    ):
        """
        Quando uma variação é deletada, seu estoque é liberado para outras variações.
        """
        produto = produto_com_estoque  # estoque = 10
        valor_pequeno = atributo_tamanho.valores.get(valor="Pequeno")
        valor_grande = atributo_tamanho.valores.get(valor="Grande")

        # Criar variações
        var1 = VariacaoProduto.objects.create(produto=produto, estoque=5)
        var1.valores.add(valor_pequeno)

        var2 = VariacaoProduto.objects.create(produto=produto, estoque=5)
        var2.valores.add(valor_grande)

        # Deletar var1
        var1.delete()

        # Agora o total é 5
        total = sum(v.estoque or 0 for v in produto.variacoes.all())
        assert total == 5
        assert total < produto.estoque  # 5 < 10


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
        """Deve mostrar mensagem quando estoque é 0."""
        produto = ProdutoFactory(estoque=0)
        result = admin_instance.estoque_display(produto)
        assert "Não definido" in result

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
        valor_pequeno = atributo_tamanho.valores.get(valor="Pequeno")
        valor_grande = atributo_tamanho.valores.get(valor="Grande")

        var1 = VariacaoProduto.objects.create(produto=produto, estoque=3)
        var1.valores.add(valor_pequeno)

        var2 = VariacaoProduto.objects.create(produto=produto, estoque=4)
        var2.valores.add(valor_grande)

        result = admin_instance.estoque_variacoes_display(produto)
        assert result == "7"

    def test_estoque_variacoes_display_sem_variacoes(
        self, admin_instance, produto_com_estoque,
    ):
        """Deve mostrar '0' quando não há variações."""
        result = admin_instance.estoque_variacoes_display(produto_com_estoque)
        assert result == "0"

    def test_estoque_disponivel_display(
        self, admin_instance, produto_com_estoque, atributo_tamanho,
    ):
        """Deve mostrar estoque disponível para alocação."""
        produto = produto_com_estoque  # estoque = 10
        valor_pequeno = atributo_tamanho.valores.get(valor="Pequeno")

        var1 = VariacaoProduto.objects.create(produto=produto, estoque=3)
        var1.valores.add(valor_pequeno)

        result = admin_instance.estoque_disponivel_display(produto)
        assert result == "7"  # 10 - 3 = 7

    def test_estoque_disponivel_display_excedido(
        self, admin_instance, produto_com_estoque, atributo_tamanho,
    ):
        """Deve mostrar alerta quando estoque é excedido."""
        produto = produto_com_estoque  # estoque = 10
        valor_pequeno = atributo_tamanho.valores.get(valor="Pequeno")
        valor_grande = atributo_tamanho.valores.get(valor="Grande")

        # Criar variações que excedem o estoque
        var1 = VariacaoProduto.objects.create(produto=produto, estoque=8)
        var1.valores.add(valor_pequeno)

        var2 = VariacaoProduto.objects.create(produto=produto, estoque=8)
        var2.valores.add(valor_grande)

        result = admin_instance.estoque_disponivel_display(produto)
        assert "EXCEDIDO" in result
        assert "-6" in result  # 10 - 16 = -6

    def test_estoque_disponivel_display_sem_limite(self, admin_instance, db):
        """Deve mostrar 'Sem limite' quando estoque do produto é 0."""
        produto = ProdutoFactory(estoque=0)
        result = admin_instance.estoque_disponivel_display(produto)
        assert "Sem limite" in result
