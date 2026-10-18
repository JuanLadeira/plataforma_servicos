from decimal import Decimal

import pytest

from plataforma_de_servicos.estoque.exceptions import InventarioSaldoInsuficienteError
from plataforma_de_servicos.estoque.exceptions import ProdutoSaldoInsuficienteError
from plataforma_de_servicos.estoque.exceptions import VariacaoSaldoInsuficienteError
from plataforma_de_servicos.estoque.models import Estoque
from plataforma_de_servicos.estoque.tests import cenarios
from plataforma_de_servicos.produto.models.produto_model import Produto

pytestmark = pytest.mark.django_db


def test_processar_duas_vezes_aplica_uma():
    dep = cenarios.deposito()
    v = cenarios.variacao_com_saldo({dep: 0})
    estoque = cenarios.entrada([(v, 5)], destino=dep)
    estoque.processar()
    Estoque.objects.get(
        pk=estoque.pk
    ).processar()  # outra instância, como faria outro request
    assert cenarios.saldos(v, dep) == (5, 5, 5)


def test_saida_maior_que_o_saldo_do_deposito_falha_mesmo_com_total_suficiente():
    dep_a, dep_b = cenarios.deposito(), cenarios.deposito()
    v = cenarios.variacao_com_saldo({dep_a: 2, dep_b: 8})
    saida = cenarios.saida([(v, 5)], origem=dep_a)
    with pytest.raises(InventarioSaldoInsuficienteError):
        saida.processar()
    assert cenarios.saldos(v, dep_a) == (10, 10, 2)
    assert cenarios.saldo_deposito(dep_b, v) == 8
    assert not Estoque.objects.get(pk=saida.pk).processado


def test_saida_de_deposito_sem_registro_de_saldo_falha():
    dep_a, dep_vazio = cenarios.deposito(), cenarios.deposito()
    produto = cenarios.produto_com_saldo({dep_a: 3})
    with pytest.raises(InventarioSaldoInsuficienteError):
        cenarios.saida([(produto, 1)], origem=dep_vazio).processar()
    assert cenarios.saldos(produto, dep_a) == (None, 3, 3)


def test_saida_maior_que_a_variacao_falha():
    dep = cenarios.deposito()
    v = cenarios.variacao_com_saldo({dep: 3})
    with pytest.raises(VariacaoSaldoInsuficienteError):
        cenarios.saida([(v, 4)], origem=dep).processar()
    assert cenarios.saldos(v, dep) == (3, 3, 3)


def test_saida_maior_que_o_produto_falha():
    dep = cenarios.deposito()
    produto = cenarios.produto_com_saldo({dep: 3})
    with pytest.raises(ProdutoSaldoInsuficienteError):
        cenarios.saida([(produto, 4)], origem=dep).processar()
    assert cenarios.saldos(produto, dep) == (None, 3, 3)


def test_falha_no_segundo_item_desfaz_o_primeiro():
    dep = cenarios.deposito()
    v1 = cenarios.variacao_com_saldo({dep: 5})
    v2 = cenarios.variacao_com_saldo({dep: 1})
    with pytest.raises(VariacaoSaldoInsuficienteError):
        cenarios.saida([(v1, 2), (v2, 3)], origem=dep).processar()
    assert cenarios.saldos(v1, dep) == (5, 5, 5)


def test_transferencia_sem_saldo_na_origem_falha():
    origem, destino = cenarios.deposito(), cenarios.deposito()
    produto = cenarios.produto_com_saldo({origem: 1, destino: 4})
    with pytest.raises(InventarioSaldoInsuficienteError):
        cenarios.transferencia(
            [(produto, 2)], origem=origem, destino=destino
        ).processar()
    assert cenarios.saldos(produto, origem) == (None, 5, 1)
    assert cenarios.saldo_deposito(destino, produto) == 4


def test_saida_nao_sobrescreve_campos_editados_do_produto():
    dep = cenarios.deposito()
    produto = cenarios.produto_com_saldo({dep: 5})
    saida = cenarios.saida([(produto, 1)], origem=dep)
    item = saida.estoque_itens.select_related("produto").get()
    Produto.objects.filter(pk=produto.pk).update(
        preco=Decimal("99.90")
    )  # edição "concorrente"
    assert item.produto.preco != Decimal("99.90")
    saida.processar()
    produto.refresh_from_db()
    assert produto.preco == Decimal("99.90")
    assert produto.estoque == 4


def test_saldo_anterior_e_saldo_do_item_refletem_valores_travados():
    dep = cenarios.deposito()
    v = cenarios.variacao_com_saldo({dep: 10})
    saida = cenarios.saida([(v, 3), (v, 2)], origem=dep)
    saida.processar()
    primeiro, segundo = saida.estoque_itens.order_by("pk")
    assert (primeiro.saldo_anterior, primeiro.saldo) == (10, 7)
    assert (segundo.saldo_anterior, segundo.saldo) == (7, 5)
    assert cenarios.saldos(v, dep) == (5, 5, 5)


def test_entrada_saida_e_transferencia_mantem_os_tres_saldos_iguais():
    dep_a, dep_b = cenarios.deposito(), cenarios.deposito()
    v = cenarios.variacao_com_saldo({dep_a: 0})
    cenarios.entrada([(v, 10)], destino=dep_a).processar()
    cenarios.saida([(v, 3)], origem=dep_a).processar()
    cenarios.transferencia([(v, 4)], origem=dep_a, destino=dep_b).processar()
    estoque_variacao, estoque_produto, saldo_a = cenarios.saldos(v, dep_a)
    saldo_b = cenarios.saldo_deposito(dep_b, v)
    assert (estoque_variacao, estoque_produto, saldo_a, saldo_b) == (7, 7, 3, 4)
    assert estoque_variacao == saldo_a + saldo_b
