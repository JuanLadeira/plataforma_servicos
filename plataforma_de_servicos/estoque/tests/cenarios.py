"""Construtores de cenários de estoque usados pelos testes de estoque e de vendas."""

from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.estoque.models import Estoque
from plataforma_de_servicos.estoque.models import EstoqueItens
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.produto.models.atributos import VariacaoProduto
from plataforma_de_servicos.produto.models.produto_model import Produto
from plataforma_de_servicos.produto.tests.factories import ProdutoFactory
from plataforma_de_servicos.produto.tests.factories import VariacaoProdutoFactory

_contador = {"n": 0}


def deposito(empresa=None, nome=None, **kwargs):
    _contador["n"] += 1
    return Inventario.objects.create(
        empresa=empresa, nome=nome or f"Depósito {_contador['n']}", **kwargs
    )


def produto_com_saldo(saldos_por_deposito, empresa=None):
    """Produto sem variação com {deposito: quantidade}; produto.estoque é a soma."""
    produto = ProdutoFactory(empresa=empresa)
    for dep, qtd in saldos_por_deposito.items():
        InventarioSaldo.objects.create(
            inventario=dep, produto=produto, variacao=None, quantidade=qtd
        )
    produto.refresh_from_db(fields=["estoque"])
    return produto


def variacao_com_saldo(saldos_por_deposito, empresa=None):
    """Variação com {deposito: quantidade}; variação e produto ficam com a soma."""
    variacao = VariacaoProdutoFactory(estoque=0, produto=ProdutoFactory(empresa=empresa))
    for dep, qtd in saldos_por_deposito.items():
        InventarioSaldo.objects.create(
            inventario=dep, produto=variacao.produto, variacao=variacao, quantidade=qtd
        )
    variacao.refresh_from_db(fields=["estoque"])
    variacao.produto.refresh_from_db(fields=["estoque"])
    return variacao


def movimento(tipo, itens, origem=None, destino=None):
    """Cria um Estoque não processado. itens: lista de (Produto ou VariacaoProduto, quantidade)."""
    estoque = Estoque.objects.create(
        empresa=(origem or destino).empresa,
        movimento=tipo,
        inventario_origem=origem,
        inventario_destino=destino,
    )
    for alvo, qtd in itens:
        variacao = alvo if isinstance(alvo, VariacaoProduto) else None
        produto = variacao.produto if variacao else alvo
        EstoqueItens.objects.create(
            estoque=estoque,
            produto=produto,
            variacao=variacao,
            quantidade=qtd,
            inventario=origem or destino,
        )
    return estoque


def entrada(itens, destino):
    return movimento(Movimento.ENTRADA.value, itens, destino=destino)


def saida(itens, origem):
    return movimento(Movimento.SAIDA.value, itens, origem=origem)


def transferencia(itens, origem, destino):
    return movimento(
        Movimento.TRANSFERENCIA.value, itens, origem=origem, destino=destino
    )


def saldo_deposito(dep, alvo):
    variacao = alvo if isinstance(alvo, VariacaoProduto) else None
    produto = variacao.produto if variacao else alvo
    linha = InventarioSaldo.objects.filter(
        inventario=dep, produto=produto, variacao=variacao
    ).first()
    return linha.quantidade if linha else 0


def saldos(alvo, dep):
    """(estoque da variação ou None, estoque do produto, saldo no depósito), relidos do banco."""
    if isinstance(alvo, VariacaoProduto):
        v = VariacaoProduto.objects.get(pk=alvo.pk)
        return (
            v.estoque,
            Produto.objects.get(pk=v.produto_id).estoque,
            saldo_deposito(dep, v),
        )
    return None, Produto.objects.get(pk=alvo.pk).estoque, saldo_deposito(dep, alvo)


def gravar_estoque(alvo, quantidade):
    """Grava direto na cópia de estoque de produto ou variação, como antes da issue #144.

    Só funciona com a fixture ``sem_trigger_de_saldo``.
    """
    type(alvo).objects.filter(pk=alvo.pk).update(estoque=quantidade)
    alvo.refresh_from_db(fields=["estoque"])
