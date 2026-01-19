import pytest
from decimal import Decimal
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


# =====================================
# TESTES PARA MODIFICADORES DE PREÇO
# =====================================

def test_valor_atributo_with_price_modifiers():
    """Testa a criação de ValorAtributo com modificadores de preço"""
    atributo = AtributoFactory(nome="Cor")
    valor = ValorAtributoFactory(
        atributo=atributo, 
        valor="Premium",
        preco_adicional=Decimal('10.00'),
        percentual_adicional=Decimal('15.50')
    )
    
    assert valor.preco_adicional == Decimal('10.00')
    assert valor.percentual_adicional == Decimal('15.50')


def test_calcular_preco_final_without_modifiers():
    """Testa cálculo de preço sem modificadores"""
    produto = ProdutoFactory(produto="Produto Teste", preco=Decimal('100.00'))
    variacao = VariacaoProdutoFactory(produto=produto, preco=Decimal('120.00'))
    
    # Remove valores padrão adicionados pela factory
    variacao.valores.clear()
    
    # Adiciona valor sem modificadores
    atributo = AtributoFactory(nome="Cor")
    valor = ValorAtributoFactory(
        atributo=atributo, 
        valor="Normal",
        preco_adicional=Decimal('0'),
        percentual_adicional=Decimal('0')
    )
    variacao.valores.add(valor)
    
    # Deve usar o preço da variação
    preco_final = variacao.calcular_preco_final()
    assert preco_final == Decimal('120.00')


def test_calcular_preco_final_with_fixed_modifier():
    """Testa cálculo de preço com modificador fixo"""
    produto = ProdutoFactory(produto="Produto Teste", preco=Decimal('100.00'))
    variacao = VariacaoProdutoFactory(produto=produto, preco=Decimal('100.00'))
    
    # Remove valores padrão
    variacao.valores.clear()
    
    # Adiciona valor com preço adicional fixo
    atributo = AtributoFactory(nome="Cor")
    valor = ValorAtributoFactory(
        atributo=atributo, 
        valor="Premium",
        preco_adicional=Decimal('25.00'),
        percentual_adicional=Decimal('0')
    )
    variacao.valores.add(valor)
    
    preco_final = variacao.calcular_preco_final()
    assert preco_final == Decimal('125.00')  # 100 + 25


def test_calcular_preco_final_with_percentage_modifier():
    """Testa cálculo de preço com modificador percentual"""
    produto = ProdutoFactory(produto="Produto Teste", preco=Decimal('100.00'))
    variacao = VariacaoProdutoFactory(produto=produto, preco=Decimal('100.00'))
    
    # Remove valores padrão
    variacao.valores.clear()
    
    # Adiciona valor com percentual adicional
    atributo = AtributoFactory(nome="Tamanho")
    valor = ValorAtributoFactory(
        atributo=atributo, 
        valor="GG",
        preco_adicional=Decimal('0'),
        percentual_adicional=Decimal('20.00')  # 20%
    )
    variacao.valores.add(valor)
    
    preco_final = variacao.calcular_preco_final()
    assert preco_final == Decimal('120.00')  # 100 + (100 * 0.20)


def test_calcular_preco_final_with_both_modifiers():
    """Testa cálculo de preço com ambos modificadores"""
    produto = ProdutoFactory(produto="Produto Teste", preco=Decimal('100.00'))
    variacao = VariacaoProdutoFactory(produto=produto, preco=Decimal('100.00'))
    
    # Remove valores padrão
    variacao.valores.clear()
    
    # Adiciona valor com ambos modificadores
    atributo = AtributoFactory(nome="Cor")
    valor = ValorAtributoFactory(
        atributo=atributo, 
        valor="Especial",
        preco_adicional=Decimal('10.00'),
        percentual_adicional=Decimal('15.00')  # 15%
    )
    variacao.valores.add(valor)
    
    preco_final = variacao.calcular_preco_final()
    # 100 (base) + 10 (fixo) + 15 (15% de 100) = 125.00
    assert preco_final == Decimal('125.00')


def test_calcular_preco_final_multiple_attributes():
    """Testa cálculo com múltiplos atributos com modificadores"""
    produto = ProdutoFactory(produto="Produto Teste", preco=Decimal('50.00'))
    variacao = VariacaoProdutoFactory(produto=produto, preco=Decimal('50.00'))
    
    # Remove valores padrão
    variacao.valores.clear()
    
    # Cor com preço adicional
    cor_attr = AtributoFactory(nome="Cor")
    valor_cor = ValorAtributoFactory(
        atributo=cor_attr, 
        valor="Dourado",
        preco_adicional=Decimal('20.00'),
        percentual_adicional=Decimal('0')
    )
    
    # Tamanho com percentual adicional
    tam_attr = AtributoFactory(nome="Tamanho")
    valor_tam = ValorAtributoFactory(
        atributo=tam_attr, 
        valor="XL",
        preco_adicional=Decimal('0'),
        percentual_adicional=Decimal('30.00')  # 30%
    )
    
    variacao.valores.add(valor_cor, valor_tam)
    
    preco_final = variacao.calcular_preco_final()
    # 50 (base) + 20 (cor) + 15 (30% de 50) = 85.00
    assert preco_final == Decimal('85.00')


def test_calcular_preco_final_fallback_to_produto_price():
    """Testa fallback para preço do produto quando variação não tem preço"""
    produto = ProdutoFactory(produto="Produto Teste", preco=Decimal('80.00'))
    variacao = VariacaoProdutoFactory(produto=produto, preco=None)
    
    # Remove valores padrão
    variacao.valores.clear()
    
    # Adiciona valor sem modificadores
    atributo = AtributoFactory(nome="Cor")
    valor = ValorAtributoFactory(
        atributo=atributo, 
        valor="Normal",
        preco_adicional=Decimal('0'),
        percentual_adicional=Decimal('0')
    )
    variacao.valores.add(valor)
    
    preco_final = variacao.calcular_preco_final()
    assert preco_final == Decimal('80.00')


def test_calcular_preco_final_no_price():
    """Testa comportamento quando não há preço definido"""
    produto = ProdutoFactory(produto="Produto Teste", preco=None)
    variacao = VariacaoProdutoFactory(produto=produto, preco=None)
    
    # Remove valores padrão
    variacao.valores.clear()
    
    # Adiciona valor com modificadores
    atributo = AtributoFactory(nome="Cor")
    valor = ValorAtributoFactory(
        atributo=atributo, 
        valor="Premium",
        preco_adicional=Decimal('10.00'),
        percentual_adicional=Decimal('15.00')
    )
    variacao.valores.add(valor)
    
    preco_final = variacao.calcular_preco_final()
    assert preco_final == Decimal('0.00')


def test_get_preco_display():
    """Testa formatação de preço para exibição"""
    produto = ProdutoFactory(produto="Produto Teste", preco=Decimal('1234.56'))
    variacao = VariacaoProdutoFactory(produto=produto, preco=Decimal('1234.56'))
    
    # Remove valores padrão
    variacao.valores.clear()
    
    # Adiciona valor sem modificadores
    atributo = AtributoFactory(nome="Cor")
    valor = ValorAtributoFactory(
        atributo=atributo, 
        valor="Normal",
        preco_adicional=Decimal('0'),
        percentual_adicional=Decimal('0')
    )
    variacao.valores.add(valor)
    
    preco_display = variacao.get_preco_display()
    assert preco_display == "R$ 1.234,56"


def test_calcular_preco_final_precision():
    """Testa precisão decimal nos cálculos"""
    produto = ProdutoFactory(produto="Produto Teste", preco=Decimal('29.99'))
    variacao = VariacaoProdutoFactory(produto=produto, preco=Decimal('29.99'))
    
    # Remove valores padrão
    variacao.valores.clear()
    
    # Percentual que gera casas decimais
    atributo = AtributoFactory(nome="Tamanho")
    valor = ValorAtributoFactory(
        atributo=atributo, 
        valor="GG",
        preco_adicional=Decimal('0'),
        percentual_adicional=Decimal('33.33')  # 33.33%
    )
    variacao.valores.add(valor)
    
    preco_final = variacao.calcular_preco_final()
    # 29.99 + (29.99 * 0.3333) = 29.99 + 9.996667 ≈ 39.99 (arredondado)
    assert preco_final == Decimal('39.99')
    
    # Verifica que tem exatamente 2 casas decimais
    assert preco_final.as_tuple().exponent == -2
