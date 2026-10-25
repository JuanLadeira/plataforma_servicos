"""O estoque é só exportado pelo import/export: entra por movimentação (issue #144)."""

import pytest
import tablib

from plataforma_de_servicos.empresa.tests.factories import EmpresaFactory
from plataforma_de_servicos.produto.resources import ProdutoResource
from plataforma_de_servicos.produto.tests.factories import ProdutoFactory

pytestmark = pytest.mark.django_db


def test_exporta_o_estoque_derivado_dos_depositos():
    produto = ProdutoFactory(empresa=EmpresaFactory(), estoque=4)
    dataset = ProdutoResource().export(
        ProdutoResource().get_queryset().filter(pk=produto.pk)
    )
    assert str(dataset.dict[0]["estoque"]) == "4"


def test_importar_ignora_a_coluna_estoque():
    produto = ProdutoFactory(empresa=EmpresaFactory(), estoque=4)
    dataset = tablib.Dataset(headers=["produto", "empresa", "ncm", "preco", "estoque"])
    dataset.append([produto.produto, produto.empresa.slug, produto.ncm, "99.00", 50])

    result = ProdutoResource().import_data(dataset, dry_run=False)

    assert not result.has_errors(), [r.errors for r in result.rows]
    produto.refresh_from_db()
    assert produto.preco == 99
    assert produto.estoque == 4
