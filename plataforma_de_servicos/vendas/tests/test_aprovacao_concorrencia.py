from decimal import Decimal

import pytest

from plataforma_de_servicos.core.tests.concorrencia import atrasar_save
from plataforma_de_servicos.core.tests.concorrencia import em_paralelo
from plataforma_de_servicos.empresa.tests.factories import EmpresaFactory
from plataforma_de_servicos.estoque.models import Estoque
from plataforma_de_servicos.estoque.tests import cenarios
from plataforma_de_servicos.produto.models.atributos import VariacaoProduto
from plataforma_de_servicos.users.tests.factories import UserFactory
from plataforma_de_servicos.vendas.models import Comissao
from plataforma_de_servicos.vendas.models import ConfiguracaoComissao
from plataforma_de_servicos.vendas.models import OrdemCompra
from plataforma_de_servicos.vendas.models import StatusOrdemCompra
from plataforma_de_servicos.vendas.services.ordem_compra_service import (
    EstoqueInsuficienteError,
)
from plataforma_de_servicos.vendas.services.ordem_compra_service import (
    OrdemCompraService,
)
from plataforma_de_servicos.vendas.tests.factories import ItemOrdemCompraFactory
from plataforma_de_servicos.vendas.tests.factories import OrdemCompraFactory

pytestmark = pytest.mark.django_db(transaction=True)


def _empresa_com_deposito():
    empresa = EmpresaFactory()
    ConfiguracaoComissao.objects.create(
        empresa=empresa, percentual_padrao=Decimal("5.00")
    )
    return empresa, cenarios.deposito(empresa=empresa, nome="Principal", padrao=True)


def _ordem(empresa, variacao, quantidade, **kwargs):
    ordem = OrdemCompraFactory(empresa=empresa, deposito_padrao=False, **kwargs)
    ItemOrdemCompraFactory(
        ordem=ordem, produto=variacao.produto, variacao=variacao, quantidade=quantidade
    )
    return ordem


def _aprovar(pk):
    usuario = UserFactory()
    return lambda: OrdemCompraService.aprovar(OrdemCompra.objects.get(pk=pk), usuario)


def test_duas_aprovacoes_simultaneas_geram_uma_saida_e_uma_comissao(monkeypatch):
    empresa, padrao = _empresa_com_deposito()
    v = cenarios.variacao_com_saldo({padrao: 10}, empresa=empresa)
    ordem = _ordem(empresa, v, 2, com_corretor=True)
    atrasar_save(monkeypatch, VariacaoProduto)

    resultados = em_paralelo(_aprovar(ordem.pk), _aprovar(ordem.pk))

    assert sorted(r[0] for r in resultados) == ["erro", "ok"], resultados
    assert Estoque.objects.filter(ordem_compra=ordem).count() == 1
    assert Comissao.objects.filter(ordem=ordem).count() == 1
    assert cenarios.saldos(v, padrao) == (8, 8, 8)


def test_duas_ordens_disputando_o_ultimo_item_so_uma_aprova(monkeypatch):
    empresa, padrao = _empresa_com_deposito()
    v = cenarios.variacao_com_saldo({padrao: 1}, empresa=empresa)
    o1, o2 = _ordem(empresa, v, 1), _ordem(empresa, v, 1)
    atrasar_save(monkeypatch, VariacaoProduto)

    resultados = em_paralelo(_aprovar(o1.pk), _aprovar(o2.pk))

    assert sorted(r[0] for r in resultados) == ["erro", "ok"], resultados
    erro = next(r[1] for r in resultados if r[0] == "erro")
    assert isinstance(erro, EstoqueInsuficienteError)
    assert cenarios.saldos(v, padrao) == (0, 0, 0)
    status = sorted(
        OrdemCompra.objects.filter(pk__in=[o1.pk, o2.pk]).values_list(
            "status", flat=True
        )
    )
    assert status == sorted(
        [StatusOrdemCompra.APROVADA, StatusOrdemCompra.PENDENTE_APROVACAO]
    )
