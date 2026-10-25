import pytest
from django.db import connection
from django.db import transaction
from django.test.utils import CaptureQueriesContext

from plataforma_de_servicos.estoque.locks import travar_saldos
from plataforma_de_servicos.estoque.tests import cenarios
from plataforma_de_servicos.inventario.models import InventarioSaldo

pytestmark = pytest.mark.django_db


def _itens(estoque):
    return list(estoque.estoque_itens.all())


def test_itens_da_mesma_variacao_compartilham_a_instancia():
    dep = cenarios.deposito()
    v = cenarios.variacao_com_saldo({dep: 10})
    estoque = cenarios.saida([(v, 1), (v, 2)], origem=dep)
    with transaction.atomic():
        travas = travar_saldos(estoque, _itens(estoque))
    assert len(travas.variacoes) == 1
    assert len(travas.produtos) == 1
    assert len(travas.saldos) == 1


def test_trava_na_ordem_saldos_variacoes_produtos():
    dep = cenarios.deposito()
    v1 = cenarios.variacao_com_saldo({dep: 10})
    v2 = cenarios.variacao_com_saldo({dep: 10})
    estoque = cenarios.saida([(v2, 1), (v1, 1)], origem=dep)
    with CaptureQueriesContext(connection) as ctx, transaction.atomic():
        travar_saldos(estoque, _itens(estoque))
    ordem = ["inventario_inventariosaldo", "produto_variacaoproduto", "produto_produto"]
    tabelas = [
        next(t for t in ordem if f'"{t}"' in q["sql"].split(" WHERE ")[0])
        for q in ctx.captured_queries
        if "FOR UPDATE" in q["sql"]
    ]
    assert tabelas == sorted(tabelas, key=ordem.index)
    assert set(tabelas) == set(ordem)


def test_cria_saldo_de_deposito_que_nao_existe():
    dep_vazio = cenarios.deposito()
    produto = cenarios.produto_com_saldo({})
    estoque = cenarios.entrada([(produto, 5)], destino=dep_vazio)
    with transaction.atomic():
        travas = travar_saldos(estoque, _itens(estoque))
    (saldo,) = travas.saldos.values()
    assert saldo.pk
    assert saldo.quantidade == 0
    assert InventarioSaldo.objects.filter(
        inventario=dep_vazio, produto=produto
    ).exists()


def test_transferencia_trava_origem_e_destino():
    origem, destino = cenarios.deposito(), cenarios.deposito()
    produto = cenarios.produto_com_saldo({origem: 5})
    estoque = cenarios.transferencia([(produto, 2)], origem=origem, destino=destino)
    with transaction.atomic():
        travas = travar_saldos(estoque, _itens(estoque))
    assert set(travas.saldos) == {
        (origem.pk, produto.pk, None),
        (destino.pk, produto.pk, None),
    }
