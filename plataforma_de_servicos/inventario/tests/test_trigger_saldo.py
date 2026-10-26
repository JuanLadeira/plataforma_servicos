"""Estoque de Produto e VariacaoProduto derivado do InventarioSaldo por trigger (issue #144)."""

import pytest
from django.db import IntegrityError
from django.db import transaction

from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.inventario.tests.factories import InventarioFactory
from plataforma_de_servicos.produto.models.atributos import VariacaoProduto
from plataforma_de_servicos.produto.models.produto_model import Produto
from plataforma_de_servicos.produto.tests.factories import ProdutoFactory
from plataforma_de_servicos.produto.tests.factories import VariacaoProdutoFactory
from plataforma_de_servicos.produto.tests.factories.atributos_factory import (
    AtributoFactory,
)
from plataforma_de_servicos.produto.tests.factories.atributos_factory import (
    ValorAtributoFactory,
)

pytestmark = pytest.mark.django_db


def _estoques(variacao):
    return (
        VariacaoProduto.objects.get(pk=variacao.pk).estoque,
        Produto.objects.get(pk=variacao.produto_id).estoque,
    )


@pytest.fixture
def variacao():
    return VariacaoProdutoFactory(estoque=0)


def test_criar_saldo_atualiza_variacao_e_produto(variacao):
    InventarioSaldo.objects.create(
        inventario=InventarioFactory(),
        produto=variacao.produto,
        variacao=variacao,
        quantidade=5,
    )
    assert _estoques(variacao) == (5, 5)


def test_soma_de_varios_depositos_e_do_saldo_sem_variacao(variacao):
    a, b = InventarioFactory(nome="A"), InventarioFactory(nome="B")
    InventarioSaldo.objects.create(
        inventario=a, produto=variacao.produto, variacao=variacao, quantidade=5
    )
    InventarioSaldo.objects.create(
        inventario=b, produto=variacao.produto, variacao=variacao, quantidade=3
    )
    InventarioSaldo.objects.create(
        inventario=b, produto=variacao.produto, variacao=None, quantidade=2
    )
    assert _estoques(variacao) == (8, 10)


def test_alterar_e_apagar_saldo_recalcula(variacao):
    saldo = InventarioSaldo.objects.create(
        inventario=InventarioFactory(),
        produto=variacao.produto,
        variacao=variacao,
        quantidade=5,
    )
    InventarioSaldo.objects.filter(pk=saldo.pk).update(quantidade=1)
    assert _estoques(variacao) == (1, 1)
    saldo.delete()
    assert _estoques(variacao) == (0, 0)


def test_trocar_a_variacao_do_saldo_acerta_as_duas(variacao):
    tamanho = AtributoFactory(nome="Tamanho", categoria=variacao.produto.categoria)
    outra = VariacaoProdutoFactory(
        produto=variacao.produto,
        estoque=0,
        valores=[ValorAtributoFactory(atributo=tamanho, valor="G")],
    )
    saldo = InventarioSaldo.objects.create(
        inventario=InventarioFactory(),
        produto=variacao.produto,
        variacao=variacao,
        quantidade=4,
    )
    InventarioSaldo.objects.filter(pk=saldo.pk).update(variacao=outra)
    assert _estoques(variacao) == (0, 4)
    assert VariacaoProduto.objects.get(pk=outra.pk).estoque == 4


def test_update_direto_no_estoque_e_recusado():
    produto = ProdutoFactory()
    with (
        pytest.raises(IntegrityError, match="derivado do InventarioSaldo"),
        transaction.atomic(),
    ):
        Produto.objects.filter(pk=produto.pk).update(estoque=99)
    variacao = VariacaoProdutoFactory(estoque=0)
    with (
        pytest.raises(IntegrityError, match="derivado do InventarioSaldo"),
        transaction.atomic(),
    ):
        VariacaoProduto.objects.filter(pk=variacao.pk).update(estoque=99)


def test_save_com_estoque_explicito_e_recusado():
    produto = ProdutoFactory()
    produto.estoque = 99
    with pytest.raises(IntegrityError), transaction.atomic():
        produto.save(update_fields=["estoque"])


def test_criar_com_estoque_diferente_de_zero_e_recusado(variacao):
    with pytest.raises(IntegrityError, match="começa em 0"), transaction.atomic():
        Produto.objects.create(
            produto="Com estoque", categoria=variacao.produto.categoria, estoque=5
        )


def test_save_comum_de_instancia_velha_nao_regrava_estoque(variacao):
    """Instância carregada antes de uma movimentação salva normalmente, sem voltar o estoque."""
    produto = Produto.objects.get(pk=variacao.produto_id)
    InventarioSaldo.objects.create(
        inventario=InventarioFactory(),
        produto=produto,
        variacao=variacao,
        quantidade=7,
    )
    produto.descricao = "editado"
    produto.save()
    assert Produto.objects.get(pk=produto.pk).estoque == 7
    assert Produto.objects.get(pk=produto.pk).descricao == "editado"


def test_saldo_zerado_novo_nao_toca_produto(variacao):
    InventarioSaldo.objects.create(
        inventario=InventarioFactory(),
        produto=variacao.produto,
        variacao=variacao,
        quantidade=0,
    )
    assert _estoques(variacao) == (0, 0)
