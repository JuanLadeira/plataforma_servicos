from io import StringIO

import pytest
from django.core.management import call_command

from plataforma_de_servicos.empresa.tests.factories import EmpresaFactory
from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.estoque.models import Estoque
from plataforma_de_servicos.estoque.tests import cenarios
from plataforma_de_servicos.vendas.models import Comissao
from plataforma_de_servicos.vendas.models import OrdemCompra
from plataforma_de_servicos.vendas.models import StatusOrdemCompra
from plataforma_de_servicos.vendas.models.comissao import StatusComissao
from plataforma_de_servicos.vendas.services.commission_service import CommissionService
from plataforma_de_servicos.vendas.services.ordem_compra_service import (
    OrdemCompraService,
)
from plataforma_de_servicos.vendas.tests.cenarios import ordem_com_itens

pytestmark = pytest.mark.django_db


def _cancelada_sem_estorno(empresa, deposito, usuario, quantidade=2):
    """Cenário de antes da correção: aprovada pelo service e cancelada só no status."""
    v = cenarios.variacao_com_saldo({deposito: 5}, empresa=empresa)
    ordem = ordem_com_itens(empresa, [(v, quantidade)], com_corretor=True)
    OrdemCompraService.aprovar(ordem, usuario)
    OrdemCompra.objects.filter(pk=ordem.pk).update(status=StatusOrdemCompra.CANCELADA)
    return ordem, v


def _rodar(*args):
    saida = StringIO()
    call_command("estornar_cancelamentos", *args, stdout=saida)
    return saida.getvalue()


def _estornos(ordem):
    return Estoque.objects.filter(ordem_compra=ordem, movimento=Movimento.ENTRADA.value)


def test_sem_aplicar_so_lista(empresa, padrao, usuario):
    ordem, v = _cancelada_sem_estorno(empresa, padrao, usuario)

    texto = _rodar()

    assert ordem.numero in texto
    assert "--aplicar" in texto
    assert cenarios.saldos(v, padrao) == (3, 3, 3)
    assert not _estornos(ordem).exists()
    assert Comissao.objects.get(ordem=ordem).status == StatusComissao.PENDENTE


def test_com_aplicar_estorna_e_e_idempotente(empresa, padrao, usuario):
    ordem, v = _cancelada_sem_estorno(empresa, padrao, usuario)

    _rodar("--aplicar")
    texto = _rodar("--aplicar")

    assert cenarios.saldos(v, padrao) == (5, 5, 5)
    assert _estornos(ordem).count() == 1
    assert Comissao.objects.get(ordem=ordem).status == StatusComissao.CANCELADA
    assert "Nenhuma ordem" in texto


def test_comissao_paga_e_pulada(empresa, padrao, usuario):
    ordem, v = _cancelada_sem_estorno(empresa, padrao, usuario)
    comissao = Comissao.objects.get(ordem=ordem)
    CommissionService(empresa).aprovar_comissao(comissao)
    CommissionService(empresa).pagar_comissao(comissao)

    texto = _rodar("--aplicar")

    assert "pulada" in texto
    assert ordem.numero in texto
    assert cenarios.saldos(v, padrao) == (3, 3, 3)
    assert not _estornos(ordem).exists()


def test_filtra_por_empresa(empresa, padrao, usuario):
    ordem, v = _cancelada_sem_estorno(empresa, padrao, usuario)
    outra = EmpresaFactory()
    deposito_outra = cenarios.deposito(empresa=outra, nome="Outra", padrao=True)
    ordem_outra, v_outra = _cancelada_sem_estorno(outra, deposito_outra, usuario)

    _rodar("--aplicar", "--empresa", outra.slug)

    assert cenarios.saldos(v, padrao) == (3, 3, 3)
    assert cenarios.saldos(v_outra, deposito_outra) == (5, 5, 5)
