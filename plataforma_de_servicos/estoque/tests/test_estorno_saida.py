import pytest
from django.db import IntegrityError

from plataforma_de_servicos.empresa.tests.factories import EmpresaFactory
from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.estoque.models import Estoque
from plataforma_de_servicos.estoque.services import EstoqueService
from plataforma_de_servicos.estoque.tests import cenarios

pytestmark = pytest.mark.django_db


@pytest.fixture
def empresa():
    return EmpresaFactory()


@pytest.fixture
def padrao(empresa):
    return cenarios.deposito(empresa=empresa, nome="Principal", padrao=True)


def test_banco_recusa_dois_estornos_da_mesma_saida(empresa, padrao):
    v = cenarios.variacao_com_saldo({padrao: 5}, empresa=empresa)
    saida = cenarios.saida([(v, 2)], origem=padrao)
    Estoque.objects.create(
        empresa=empresa,
        movimento=Movimento.ENTRADA.value,
        inventario_destino=padrao,
        estorno_de=saida,
    )
    with pytest.raises(IntegrityError):
        Estoque.objects.create(
            empresa=empresa,
            movimento=Movimento.ENTRADA.value,
            inventario_destino=padrao,
            estorno_de=saida,
        )


def _saida_processada(empresa, padrao, saldo=5, quantidade=2):
    v = cenarios.variacao_com_saldo({padrao: saldo}, empresa=empresa)
    saida = cenarios.saida([(v, quantidade)], origem=padrao)
    saida.processar()
    return v, saida


def test_estorno_devolve_ao_deposito_da_saida(empresa, padrao):
    v, saida = _saida_processada(empresa, padrao)
    assert cenarios.saldos(v, padrao) == (3, 3, 3)

    entrada = EstoqueService.criar_estorno_de_saida(saida)

    assert cenarios.saldos(v, padrao) == (5, 5, 5)
    assert entrada.movimento == Movimento.ENTRADA.value
    assert entrada.processado
    assert entrada.inventario_destino == padrao
    assert entrada.estorno_de == saida
    assert entrada.empresa == empresa
    itens = [
        (i.produto_id, i.variacao_id, i.quantidade) for i in entrada.estoque_itens.all()
    ]
    assert itens == [(v.produto_id, v.pk, 2)]


def test_estorno_recusa_saida_nao_processada(empresa, padrao):
    v = cenarios.variacao_com_saldo({padrao: 5}, empresa=empresa)
    saida = cenarios.saida([(v, 2)], origem=padrao)
    with pytest.raises(ValueError, match="processada"):
        EstoqueService.criar_estorno_de_saida(saida)


def test_estorno_recusa_entrada(empresa, padrao):
    v = cenarios.variacao_com_saldo({padrao: 5}, empresa=empresa)
    entrada = cenarios.entrada([(v, 2)], destino=padrao)
    entrada.processar()
    with pytest.raises(ValueError, match="processada"):
        EstoqueService.criar_estorno_de_saida(entrada)


def test_segundo_estorno_da_mesma_saida_e_recusado(empresa, padrao):
    v, saida = _saida_processada(empresa, padrao)
    EstoqueService.criar_estorno_de_saida(saida)
    with pytest.raises(ValueError, match="já estornada"):
        EstoqueService.criar_estorno_de_saida(saida)
    assert cenarios.saldos(v, padrao) == (5, 5, 5)
