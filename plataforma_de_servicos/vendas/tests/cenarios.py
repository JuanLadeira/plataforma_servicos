"""Construtores de ordens usados pelos testes de vendas."""

from plataforma_de_servicos.produto.models.atributos import VariacaoProduto
from plataforma_de_servicos.vendas.tests.factories import ItemOrdemCompraFactory
from plataforma_de_servicos.vendas.tests.factories import OrdemCompraFactory


def ordem_com_itens(empresa, itens, **kwargs):
    """Ordem pendente com itens [(Produto ou VariacaoProduto, quantidade)], sem criar depósito padrão."""
    ordem = OrdemCompraFactory(empresa=empresa, deposito_padrao=False, **kwargs)
    for alvo, qtd in itens:
        variacao = alvo if isinstance(alvo, VariacaoProduto) else None
        produto = variacao.produto if variacao else alvo
        ItemOrdemCompraFactory(
            ordem=ordem, produto=produto, variacao=variacao, quantidade=qtd
        )
    return ordem
