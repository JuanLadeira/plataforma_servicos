import pytest
from ..models import Atributo, ValorAtributo, VariacaoProduto
from .factories import (
    ProdutoFactory,
    AtributoFactory,
    ValorAtributoFactory,
    VariacaoProdutoFactory,
)

pytestmark = pytest.mark.django_db


def test_atributo_creation():
    atributo = AtributoFactory(nome="Teste Atributo")
    assert Atributo.objects.count() == 1
    assert atributo.nome == "Teste Atributo"
    assert str(atributo) == "Teste Atributo"


def test_valor_atributo_creation():
    atributo = AtributoFactory(nome="Cor")
    valor = ValorAtributoFactory(atributo=atributo, valor="Azul")
    assert ValorAtributo.objects.count() == 1
    assert valor.atributo == atributo
    assert valor.valor == "Azul"
    assert str(valor) == "Cor: Azul"


def test_variacao_produto_creation():
    variacao = VariacaoProdutoFactory()
    assert VariacaoProduto.objects.count() == 1
    assert variacao.valores.count() > 0
    assert variacao.produto is not None
    assert variacao.preco is not None
    assert variacao.estoque >= 10


def test_variacao_produto_sku_generation():
    # Ao criar o produto, definimos o nome que será usado para gerar o slug
    produto = ProdutoFactory(produto="Camiseta Legal")
    cor_attr = AtributoFactory(nome="Cor")
    tam_attr = AtributoFactory(nome="Tamanho")

    # Os IDs podem variar, então pegamos eles dinamicamente
    valor_cor = ValorAtributoFactory(atributo=cor_attr, valor="Verde")
    valor_tam = ValorAtributoFactory(atributo=tam_attr, valor="G")

    variacao = VariacaoProdutoFactory(
        produto=produto,
        valores=[valor_cor, valor_tam]
    )

    # A factory já chama o gerar_sku
    variacao.refresh_from_db()

    # Ordena os IDs para garantir a consistência do SKU
    ids_ordenados = sorted([valor_cor.id, valor_tam.id])
    # O slug será 'camiseta-legal' a partir do nome 'Camiseta Legal'
    expected_sku = f"camiseta-legal-{ids_ordenados[0]}-{ids_ordenados[1]}"

    assert variacao.sku == expected_sku


def test_variacao_str_representation():
    produto = ProdutoFactory(produto="Camiseta")
    cor_attr = AtributoFactory(nome="Cor")
    tam_attr = AtributoFactory(nome="Tamanho")
    valor_cor = ValorAtributoFactory(atributo=cor_attr, valor="Preto")
    valor_tam = ValorAtributoFactory(atributo=tam_attr, valor="P")

    variacao = VariacaoProdutoFactory(
        produto=produto,
        valores=[valor_cor, valor_tam]
    )
    variacao.refresh_from_db()

    # A ordem na string pode variar, então verificamos as partes
    str_repr = str(variacao)
    assert "Camiseta" in str_repr
    assert "Cor: Preto" in str_repr
    assert "Tamanho: P" in str_repr
