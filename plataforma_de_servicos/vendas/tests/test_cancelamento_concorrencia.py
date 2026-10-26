import pytest

from plataforma_de_servicos.core.tests.concorrencia import atrasar_save
from plataforma_de_servicos.core.tests.concorrencia import em_paralelo
from plataforma_de_servicos.estoque import saldos
from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.estoque.models import Estoque
from plataforma_de_servicos.estoque.tests import cenarios
from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.produto.models.atributos import VariacaoProduto
from plataforma_de_servicos.produto.models.produto_model import Produto
from plataforma_de_servicos.users.tests.factories import UserFactory
from plataforma_de_servicos.vendas.models import Comissao
from plataforma_de_servicos.vendas.models import OrdemCompra
from plataforma_de_servicos.vendas.models import StatusOrdemCompra
from plataforma_de_servicos.vendas.models.comissao import StatusComissao
from plataforma_de_servicos.vendas.services.commission_service import CommissionService
from plataforma_de_servicos.vendas.services.ordem_compra_service import (
    OrdemCompraService,
)
from plataforma_de_servicos.vendas.tests.cenarios import ordem_com_itens

pytestmark = pytest.mark.django_db(transaction=True)


def _cancelar(pk):
    usuario = UserFactory()
    return lambda: OrdemCompraService.cancelar(
        OrdemCompra.objects.get(pk=pk), usuario=usuario
    )


def _aprovar(pk):
    usuario = UserFactory()
    return lambda: OrdemCompraService.aprovar(OrdemCompra.objects.get(pk=pk), usuario)


def test_dois_cancelamentos_simultaneos_estornam_uma_vez(
    monkeypatch, empresa, padrao, usuario
):
    v = cenarios.variacao_com_saldo({padrao: 10}, empresa=empresa)
    ordem = OrdemCompraService.aprovar(ordem_com_itens(empresa, [(v, 2)]), usuario)
    atrasar_save(monkeypatch, VariacaoProduto)

    resultados = em_paralelo(_cancelar(ordem.pk), _cancelar(ordem.pk))

    assert sorted(r[0] for r in resultados) == ["erro", "ok"], resultados
    assert (
        Estoque.objects.filter(
            ordem_compra=ordem, movimento=Movimento.ENTRADA.value
        ).count()
        == 1
    )
    assert cenarios.saldos(v, padrao) == (10, 10, 10)


def test_cancelamento_e_pagamento_simultaneos_nunca_terminam_os_dois(
    monkeypatch, empresa, padrao, usuario
):
    v = cenarios.variacao_com_saldo({padrao: 10}, empresa=empresa)
    ordem = OrdemCompraService.aprovar(
        ordem_com_itens(empresa, [(v, 2)], com_corretor=True), usuario
    )
    comissao = Comissao.objects.get(ordem=ordem)
    CommissionService(empresa).aprovar_comissao(comissao)
    atrasar_save(monkeypatch, Comissao)

    def pagar():
        return CommissionService(empresa).pagar_comissao(
            Comissao.objects.get(pk=comissao.pk)
        )

    em_paralelo(_cancelar(ordem.pk), pagar)

    ordem.refresh_from_db()
    status_comissao = Comissao.objects.get(pk=comissao.pk).status
    if ordem.status == StatusOrdemCompra.CANCELADA:
        assert status_comissao == StatusComissao.CANCELADA
        assert cenarios.saldos(v, padrao) == (10, 10, 10)
    else:
        assert ordem.status == StatusOrdemCompra.APROVADA
        assert status_comissao == StatusComissao.PAGA
        assert cenarios.saldos(v, padrao) == (8, 8, 8)


def test_cancelar_uma_e_aprovar_outra_no_mesmo_item_sem_deadlock(
    monkeypatch, empresa, padrao, usuario
):
    v = cenarios.variacao_com_saldo({padrao: 3}, empresa=empresa)
    aprovada = OrdemCompraService.aprovar(ordem_com_itens(empresa, [(v, 2)]), usuario)
    pendente = ordem_com_itens(empresa, [(v, 3)])
    atrasar_save(monkeypatch, VariacaoProduto)

    resultados = em_paralelo(_cancelar(aprovada.pk), _aprovar(pendente.pk))

    # a aprovação só cabe se o estorno vier antes; os saldos batem nos dois casos
    assert resultados[0][0] == "ok", resultados
    esperado = 0 if resultados[1][0] == "ok" else 3
    assert cenarios.saldos(v, padrao) == (esperado, esperado, esperado)
    assert not saldos.variacoes_divergentes(VariacaoProduto, InventarioSaldo).exists()
    assert not saldos.produtos_divergentes(Produto, InventarioSaldo).exists()
