import pytest
from django.db import IntegrityError
from django.db import transaction

from plataforma_de_servicos.estoque.saldos_migracao import checar_antes_das_constraints
from plataforma_de_servicos.inventario.tests.factories import InventarioFactory
from plataforma_de_servicos.inventario.tests.factories import InventarioSaldoFactory
from plataforma_de_servicos.produto.tests.factories import ProdutoFactory

pytestmark = pytest.mark.django_db


def test_saldo_de_deposito_nao_pode_ser_negativo():
    s = InventarioSaldoFactory(quantidade=1)
    s.quantidade = -1
    with pytest.raises(IntegrityError), transaction.atomic():
        s.save()


def test_estoque_de_produto_nao_pode_ser_gravado_direto():
    # Derivado do InventarioSaldo (issue #144): o trigger de guarda recusa antes do CHECK.
    p = ProdutoFactory()
    p.estoque = -1
    with pytest.raises(IntegrityError), transaction.atomic():
        p.save(update_fields=["estoque"])


def test_saldo_duplicado_sem_variacao_e_recusado():
    inv, prod = InventarioFactory(), ProdutoFactory()
    InventarioSaldoFactory(inventario=inv, produto=prod, variacao=None)
    with pytest.raises(IntegrityError), transaction.atomic():
        InventarioSaldoFactory(inventario=inv, produto=prod, variacao=None)


def test_checagem_previa_lista_os_negativos():
    with pytest.raises(RuntimeError, match="verificar_saldos") as erro:
        checar_antes_das_constraints(negativos=["saldo 1"], duplicados=[])
    assert "saldo 1" in str(erro.value)


def test_checagem_previa_lista_os_duplicados():
    with pytest.raises(RuntimeError, match="saldo duplicado"):
        checar_antes_das_constraints(negativos=[], duplicados=[{"inventario_id": 1}])


def test_checagem_previa_passa_sem_problemas():
    checar_antes_das_constraints(negativos=[], duplicados=[])
