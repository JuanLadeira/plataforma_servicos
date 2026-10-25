import pytest

from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.estoque.models import Estoque
from plataforma_de_servicos.estoque.tests import cenarios
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.vendas.models import Comissao
from plataforma_de_servicos.vendas.models import StatusOrdemCompra
from plataforma_de_servicos.vendas.models.comissao import StatusComissao
from plataforma_de_servicos.vendas.services.commission_service import CommissionService
from plataforma_de_servicos.vendas.services.ordem_compra_service import ComissaoPagaError
from plataforma_de_servicos.vendas.services.ordem_compra_service import (
    OrdemCompraService,
)
from plataforma_de_servicos.vendas.tests.cenarios import ordem_com_itens
from plataforma_de_servicos.vendas.tests.factories import ItemOrdemCompraFactory

pytestmark = pytest.mark.django_db


def _aprovada(empresa, itens, usuario, **kwargs):
    ordem = ordem_com_itens(empresa, itens, **kwargs)
    return OrdemCompraService.aprovar(ordem, usuario)


def _estornos(ordem):
    return Estoque.objects.filter(ordem_compra=ordem, movimento=Movimento.ENTRADA.value)


def test_cancelar_aprovada_devolve_estoque_e_cancela_comissao(empresa, padrao, usuario):
    v = cenarios.variacao_com_saldo({padrao: 5}, empresa=empresa)
    ordem = _aprovada(empresa, [(v, 2)], usuario, com_corretor=True)
    assert cenarios.saldos(v, padrao) == (3, 3, 3)

    ordem = OrdemCompraService.cancelar(ordem, "cliente desistiu", usuario=usuario)

    assert ordem.status == StatusOrdemCompra.CANCELADA
    assert ordem.cancelado_por == usuario
    assert ordem.data_cancelamento is not None
    assert cenarios.saldos(v, padrao) == (5, 5, 5)
    saida = Estoque.objects.get(ordem_compra=ordem, movimento=Movimento.SAIDA.value)
    entrada = _estornos(ordem).get()
    assert entrada.estorno_de == saida
    assert entrada.processado
    comissao = Comissao.objects.get(ordem=ordem)
    assert comissao.status == StatusComissao.CANCELADA
    assert "cliente desistiu" in comissao.observacoes


def test_estorno_vai_para_o_deposito_da_saida(empresa, padrao, usuario):
    novo = cenarios.deposito(empresa=empresa, nome="Novo")
    v = cenarios.variacao_com_saldo({padrao: 5, novo: 0}, empresa=empresa)
    ordem = _aprovada(empresa, [(v, 2)], usuario)
    Inventario.objects.filter(pk=padrao.pk).update(padrao=False)
    Inventario.objects.filter(pk=novo.pk).update(padrao=True)

    OrdemCompraService.cancelar(ordem, usuario=usuario)

    assert cenarios.saldo_deposito(padrao, v) == 5
    assert cenarios.saldo_deposito(novo, v) == 0


def test_item_sem_produto_nao_gera_estorno(empresa, padrao, usuario):
    produto = cenarios.produto_com_saldo({padrao: 5}, empresa=empresa)
    ordem = ordem_com_itens(empresa, [(produto, 1)])
    ItemOrdemCompraFactory(ordem=ordem, quantidade=3)
    OrdemCompraService.aprovar(ordem, usuario)

    OrdemCompraService.cancelar(ordem, usuario=usuario)

    assert cenarios.saldos(produto, padrao) == (None, 5, 5)
    assert _estornos(ordem).get().estoque_itens.count() == 1


def test_aprovada_sem_corretor(empresa, padrao, usuario):
    v = cenarios.variacao_com_saldo({padrao: 5}, empresa=empresa)
    ordem = _aprovada(empresa, [(v, 2)], usuario)

    ordem = OrdemCompraService.cancelar(ordem, usuario=usuario)

    assert ordem.status == StatusOrdemCompra.CANCELADA
    assert cenarios.saldos(v, padrao) == (5, 5, 5)
    assert not Comissao.objects.filter(ordem=ordem).exists()


def test_comissao_paga_bloqueia_cancelamento(empresa, padrao, usuario):
    v = cenarios.variacao_com_saldo({padrao: 5}, empresa=empresa)
    ordem = _aprovada(empresa, [(v, 2)], usuario, com_corretor=True)
    servico = CommissionService(empresa)
    comissao = Comissao.objects.get(ordem=ordem)
    servico.aprovar_comissao(comissao)
    servico.pagar_comissao(comissao)

    with pytest.raises(ComissaoPagaError, match="já paga"):
        OrdemCompraService.cancelar(ordem, usuario=usuario)

    ordem.refresh_from_db()
    assert ordem.status == StatusOrdemCompra.APROVADA
    assert ordem.cancelado_por is None
    assert cenarios.saldos(v, padrao) == (3, 3, 3)
    assert not _estornos(ordem).exists()
    assert Comissao.objects.get(ordem=ordem).status == StatusComissao.PAGA


def test_comissao_aprovada_e_cancelada(empresa, padrao, usuario):
    v = cenarios.variacao_com_saldo({padrao: 5}, empresa=empresa)
    ordem = _aprovada(empresa, [(v, 2)], usuario, com_corretor=True)
    CommissionService(empresa).aprovar_comissao(Comissao.objects.get(ordem=ordem))

    OrdemCompraService.cancelar(ordem, usuario=usuario)

    assert Comissao.objects.get(ordem=ordem).status == StatusComissao.CANCELADA


def test_cancelar_pendente_nao_cria_movimentacao(empresa, padrao, usuario):
    v = cenarios.variacao_com_saldo({padrao: 5}, empresa=empresa)
    ordem = ordem_com_itens(empresa, [(v, 2)])

    ordem = OrdemCompraService.cancelar(ordem, usuario=usuario)

    assert ordem.status == StatusOrdemCompra.CANCELADA
    assert ordem.cancelado_por == usuario
    assert not Estoque.objects.filter(ordem_compra=ordem).exists()
    assert cenarios.saldos(v, padrao) == (5, 5, 5)
