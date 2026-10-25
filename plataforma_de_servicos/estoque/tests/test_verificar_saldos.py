import pytest
from django.core.management import call_command

from plataforma_de_servicos.empresa.tests.factories import EmpresaFactory
from plataforma_de_servicos.estoque import saldos
from plataforma_de_servicos.estoque.models import Estoque
from plataforma_de_servicos.estoque.tests.cenarios import gravar_estoque
from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.inventario.tests.factories import InventarioFactory
from plataforma_de_servicos.inventario.tests.factories import InventarioSaldoFactory
from plataforma_de_servicos.produto.models.atributos import VariacaoProduto
from plataforma_de_servicos.produto.models.produto_model import Produto
from plataforma_de_servicos.produto.tests.factories import ProdutoFactory
from plataforma_de_servicos.produto.tests.factories import VariacaoProdutoFactory

pytestmark = pytest.mark.django_db


def _corrigir():
    return saldos.corrigir(Produto, VariacaoProduto, InventarioSaldo)


def saldos_por_alvo(deposito, produto):
    return dict(
        InventarioSaldo.objects.filter(inventario=deposito, produto=produto).values_list(
            "variacao_id", "quantidade"
        )
    )


def test_lista_saldo_negativo_de_deposito(sem_constraints_de_saldo):
    s = InventarioSaldoFactory(quantidade=-3)
    assert list(saldos.saldos_negativos(InventarioSaldo)) == [s]


def test_lista_saldo_duplicado(sem_constraints_de_saldo):
    inv, prod = InventarioFactory(), ProdutoFactory()
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
    inv, prod = InventarioFactory(), ProdutoFactory()
    InventarioSaldoFactory(inventario=inv, produto=prod, quantidade=2)
    InventarioSaldoFactory(inventario=inv, produto=prod, quantidade=3)
    _corrigir()
    (saldo,) = InventarioSaldo.objects.filter(inventario=inv, produto=prod)
    assert saldo.quantidade == 5


def test_lista_divergencia_entre_variacao_e_depositos(sem_trigger_de_saldo):
    v = VariacaoProdutoFactory(estoque=0)
    InventarioSaldoFactory(produto=v.produto, variacao=v, quantidade=7)
    gravar_estoque(v, 10)
    divergentes = list(saldos.variacoes_divergentes(VariacaoProduto, InventarioSaldo))
    assert [(d.pk, d.estoque, d.total_depositos) for d in divergentes] == [
        (v.pk, 10, 7)
    ]


def test_variacao_igual_a_soma_de_dois_depositos_nao_diverge():
    v = VariacaoProdutoFactory(estoque=0)
    InventarioSaldoFactory(produto=v.produto, variacao=v, quantidade=7)
    InventarioSaldoFactory(produto=v.produto, variacao=v, quantidade=3)
    assert not saldos.variacoes_divergentes(VariacaoProduto, InventarioSaldo).exists()


def test_com_o_trigger_produto_e_variacao_nunca_divergem():
    v = VariacaoProdutoFactory(estoque=4)
    InventarioSaldoFactory(produto=v.produto, quantidade=3)
    assert not saldos.variacoes_divergentes(VariacaoProduto, InventarioSaldo).exists()
    assert not saldos.produtos_divergentes(Produto, InventarioSaldo).exists()


def test_produto_sem_deposito_e_listado(sem_trigger_de_saldo):
    p = ProdutoFactory()
    gravar_estoque(p, 5)
    assert list(saldos.produtos_sem_deposito(Produto, InventarioSaldo)) == [p]


def test_produto_sem_deposito_com_estoque_so_na_variacao_e_listado(sem_trigger_de_saldo):
    v = VariacaoProdutoFactory(estoque=0)
    gravar_estoque(v, 3)
    assert list(saldos.produtos_sem_deposito(Produto, InventarioSaldo)) == [v.produto]


def test_corrigir_da_entrada_no_deposito_padrao_para_produto_sem_deposito(sem_trigger_de_saldo):
    empresa = EmpresaFactory()
    padrao = InventarioFactory(empresa=empresa, nome="Padrão", padrao=True)
    v = VariacaoProdutoFactory(estoque=0, produto=ProdutoFactory(empresa=empresa))
    gravar_estoque(v, 3)
    gravar_estoque(v.produto, 7)
    _corrigir()
    entrada = Estoque.objects.get(inventario_destino=padrao)
    assert entrada.processado
    assert {i.variacao_id: i.quantidade for i in entrada.estoque_itens.all()} == {v.pk: 3, None: 4}
    assert saldos_por_alvo(padrao, v.produto) == {v.pk: 3, None: 4}
    assert not saldos.produtos_sem_deposito(Produto, InventarioSaldo).exists()


def test_corrigir_sem_deposito_padrao_deixa_o_produto_listado(sem_trigger_de_saldo):
    p = ProdutoFactory(empresa=EmpresaFactory())
    gravar_estoque(p, 5)
    assert _corrigir() == [p]
    assert list(saldos.produtos_sem_deposito(Produto, InventarioSaldo)) == [p]


def test_corrigir_recalcula_produto_e_variacao_a_partir_dos_depositos(sem_trigger_de_saldo):
    v = VariacaoProdutoFactory(estoque=0)
    InventarioSaldoFactory(produto=v.produto, variacao=v, quantidade=7)
    gravar_estoque(v, 10)
    gravar_estoque(v.produto, 10)
    _corrigir()
    v.refresh_from_db()
    v.produto.refresh_from_db()
    assert v.estoque == 7
    assert v.produto.estoque == 7


def test_corrigir_recalcula_mesmo_com_os_triggers_instalados():
    """Depois da migration o banco recusa gravar estoque, mas o recálculo do --corrigir passa."""
    from django.db import connection

    v = VariacaoProdutoFactory(estoque=0)
    InventarioSaldoFactory(produto=v.produto, variacao=v, quantidade=7)
    with connection.cursor() as cursor:
        # Simula uma cópia que divergiu (ex.: trigger desligado por um tempo).
        cursor.execute("SELECT set_config('app.sync_saldo', 'on', true)")
        VariacaoProduto.objects.filter(pk=v.pk).update(estoque=10)
        cursor.execute("SELECT set_config('app.sync_saldo', 'off', true)")
    _corrigir()
    v.refresh_from_db()
    assert v.estoque == 7


def test_corrigir_nao_mexe_em_saldo_negativo_de_deposito(sem_constraints_de_saldo):
    s = InventarioSaldoFactory(quantidade=-3)
    _corrigir()
    s.refresh_from_db()
    assert s.quantidade == -3


def test_filtro_por_empresa(sem_trigger_de_saldo):
    empresa_a, empresa_b = EmpresaFactory(), EmpresaFactory()
    va = VariacaoProdutoFactory(estoque=0, produto=ProdutoFactory(empresa=empresa_a))
    vb = VariacaoProdutoFactory(estoque=0, produto=ProdutoFactory(empresa=empresa_b))
    InventarioSaldoFactory(produto=va.produto, variacao=va, quantidade=1)
    InventarioSaldoFactory(produto=vb.produto, variacao=vb, quantidade=1)
    gravar_estoque(va, 10)
    gravar_estoque(vb, 10)
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


def test_comando_corrigir_resolve_divergencia(sem_trigger_de_saldo, capsys):
    v = VariacaoProdutoFactory(estoque=0)
    InventarioSaldoFactory(produto=v.produto, variacao=v, quantidade=7)
    gravar_estoque(v, 10)
    gravar_estoque(v.produto, 10)
    call_command("verificar_saldos", "--corrigir")
    assert "nenhum problema" in capsys.readouterr().out.lower()
