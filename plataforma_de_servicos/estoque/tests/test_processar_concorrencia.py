import pytest

from plataforma_de_servicos.core.tests.concorrencia import atrasar_save
from plataforma_de_servicos.core.tests.concorrencia import em_paralelo
from plataforma_de_servicos.estoque.models import Estoque
from plataforma_de_servicos.estoque.tests import cenarios
from plataforma_de_servicos.produto.models.atributos import VariacaoProduto

pytestmark = pytest.mark.django_db(transaction=True)


def test_mesma_movimentacao_em_paralelo_aplica_uma_vez(monkeypatch):
    dep = cenarios.deposito()
    v = cenarios.variacao_com_saldo({dep: 0})
    estoque = cenarios.entrada([(v, 5)], destino=dep)
    atrasar_save(monkeypatch, VariacaoProduto)
    em_paralelo(
        lambda: Estoque.objects.get(pk=estoque.pk).processar(),
        lambda: Estoque.objects.get(pk=estoque.pk).processar(),
    )
    assert cenarios.saldos(v, dep) == (5, 5, 5)


def test_duas_saidas_simultaneas_terminam_com_os_tres_saldos_corretos(monkeypatch):
    dep = cenarios.deposito()
    v = cenarios.variacao_com_saldo({dep: 10})
    s1, s2 = cenarios.saida([(v, 1)], origem=dep), cenarios.saida([(v, 1)], origem=dep)
    atrasar_save(monkeypatch, VariacaoProduto)
    resultados = em_paralelo(s1.processar, s2.processar)
    assert [r[0] for r in resultados] == ["ok", "ok"], resultados
    assert cenarios.saldos(v, dep) == (8, 8, 8)


def test_saidas_simultaneas_acima_do_saldo_uma_falha(monkeypatch):
    dep = cenarios.deposito()
    v = cenarios.variacao_com_saldo({dep: 10})
    s1, s2 = cenarios.saida([(v, 6)], origem=dep), cenarios.saida([(v, 6)], origem=dep)
    atrasar_save(monkeypatch, VariacaoProduto)
    resultados = em_paralelo(s1.processar, s2.processar)
    assert sorted(r[0] for r in resultados) == ["erro", "ok"], resultados
    assert cenarios.saldos(v, dep) == (4, 4, 4)


def test_movimentacoes_cruzadas_nao_entram_em_deadlock(monkeypatch):
    dep = cenarios.deposito()
    a = cenarios.variacao_com_saldo({dep: 10})
    b = cenarios.variacao_com_saldo({dep: 10})
    m1 = cenarios.saida([(a, 1), (b, 1)], origem=dep)
    m2 = cenarios.saida([(b, 1), (a, 1)], origem=dep)
    atrasar_save(monkeypatch, VariacaoProduto)
    resultados = em_paralelo(m1.processar, m2.processar)
    assert [r[0] for r in resultados] == ["ok", "ok"], resultados
    assert cenarios.saldos(a, dep) == (8, 8, 8)
    assert cenarios.saldos(b, dep) == (8, 8, 8)
