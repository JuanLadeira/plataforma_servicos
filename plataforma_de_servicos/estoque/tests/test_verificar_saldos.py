import pytest
from django.core.management import call_command

from plataforma_de_servicos.empresa.tests.factories import EmpresaFactory
from plataforma_de_servicos.estoque import saldos
from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.inventario.tests.factories import InventarioFactory
from plataforma_de_servicos.inventario.tests.factories import InventarioSaldoFactory
from plataforma_de_servicos.produto.models.atributos import VariacaoProduto
from plataforma_de_servicos.produto.models.produto_model import Produto
from plataforma_de_servicos.produto.tests.factories import ProdutoFactory
from plataforma_de_servicos.produto.tests.factories import VariacaoProdutoFactory

pytestmark = pytest.mark.django_db


def _corrigir():
    saldos.corrigir(Produto, VariacaoProduto, InventarioSaldo)


def test_lista_saldo_negativo_de_deposito(sem_constraints_de_saldo):
    s = InventarioSaldoFactory(quantidade=-3)
    assert list(saldos.saldos_negativos(InventarioSaldo)) == [s]


def test_lista_saldo_duplicado(sem_constraints_de_saldo):
    inv, prod = InventarioFactory(), ProdutoFactory(estoque=0)
    InventarioSaldoFactory(inventario=inv, produto=prod, quantidade=2)
    InventarioSaldoFactory(inventario=inv, produto=prod, quantidade=3)
    (dup,) = saldos.saldos_duplicados(InventarioSaldo)
    assert (dup["inventario_id"], dup["produto_id"], dup["variacao_id"], dup["n"]) == (
        inv.pk,
        prod.pk,
        None,
        2,
    )


def test_corrigir_junta_duplicados_somando(sem_constraints_de_saldo):
    inv, prod = InventarioFactory(), ProdutoFactory(estoque=5)
    InventarioSaldoFactory(inventario=inv, produto=prod, quantidade=2)
    InventarioSaldoFactory(inventario=inv, produto=prod, quantidade=3)
    _corrigir()
    (saldo,) = InventarioSaldo.objects.filter(inventario=inv, produto=prod)
    assert saldo.quantidade == 5


def test_lista_divergencia_entre_variacao_e_depositos():
    v = VariacaoProdutoFactory(estoque=10)
    InventarioSaldoFactory(produto=v.produto, variacao=v, quantidade=7)
    divergentes = list(saldos.variacoes_divergentes(VariacaoProduto, InventarioSaldo))
    assert [(d.pk, d.estoque, d.total_depositos) for d in divergentes] == [
        (v.pk, 10, 7)
    ]


def test_variacao_igual_a_soma_de_dois_depositos_nao_diverge():
    v = VariacaoProdutoFactory(estoque=10)
    InventarioSaldoFactory(produto=v.produto, variacao=v, quantidade=7)
    InventarioSaldoFactory(produto=v.produto, variacao=v, quantidade=3)
    assert not saldos.variacoes_divergentes(VariacaoProduto, InventarioSaldo).exists()


def test_produto_sem_nenhum_deposito_e_listado_a_parte_e_nao_e_corrigido():
    p = ProdutoFactory(estoque=5)
    assert p in saldos.produtos_sem_deposito(Produto, InventarioSaldo)
    _corrigir()
    p.refresh_from_db()
    assert p.estoque == 5


def test_corrigir_recalcula_produto_e_variacao_a_partir_dos_depositos():
    v = VariacaoProdutoFactory(estoque=10)
    v.produto.estoque = 10
    v.produto.save()
    InventarioSaldoFactory(produto=v.produto, variacao=v, quantidade=7)
    _corrigir()
    v.refresh_from_db()
    v.produto.refresh_from_db()
    assert v.estoque == 7
    assert v.produto.estoque == 7


def test_corrigir_nao_mexe_em_saldo_negativo_de_deposito(sem_constraints_de_saldo):
    s = InventarioSaldoFactory(quantidade=-3)
    _corrigir()
    s.refresh_from_db()
    assert s.quantidade == -3


def test_filtro_por_empresa():
    empresa_a, empresa_b = EmpresaFactory(), EmpresaFactory()
    va = VariacaoProdutoFactory(estoque=10, produto=ProdutoFactory(empresa=empresa_a))
    vb = VariacaoProdutoFactory(estoque=10, produto=ProdutoFactory(empresa=empresa_b))
    InventarioSaldoFactory(produto=va.produto, variacao=va, quantidade=1)
    InventarioSaldoFactory(produto=vb.produto, variacao=vb, quantidade=1)
    divergentes = saldos.variacoes_divergentes(
        VariacaoProduto, InventarioSaldo, empresa=empresa_a.slug
    )
    assert list(divergentes) == [va]


def test_comando_sai_com_codigo_1_quando_ha_problema(sem_constraints_de_saldo, capsys):
    InventarioSaldoFactory(quantidade=-1)
    with pytest.raises(SystemExit) as saida:
        call_command("verificar_saldos")
    assert saida.value.code == 1
    assert "negativo" in capsys.readouterr().out.lower()


def test_comando_sem_problemas_termina_ok(capsys):
    call_command("verificar_saldos")
    assert "nenhum problema" in capsys.readouterr().out.lower()


def test_comando_corrigir_resolve_divergencia(capsys):
    v = VariacaoProdutoFactory(estoque=10)
    v.produto.estoque = 10
    v.produto.save()
    InventarioSaldoFactory(produto=v.produto, variacao=v, quantidade=7)
    call_command("verificar_saldos", "--corrigir")
    assert "nenhum problema" in capsys.readouterr().out.lower()
