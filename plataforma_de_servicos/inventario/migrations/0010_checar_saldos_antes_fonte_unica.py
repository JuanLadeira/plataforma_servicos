from django.db import migrations


def checar(apps, schema_editor):
    """Para a migration se as cópias de saldo não batem com a soma dos depósitos."""
    from plataforma_de_servicos.estoque.saldos import produtos_divergentes
    from plataforma_de_servicos.estoque.saldos import produtos_sem_deposito
    from plataforma_de_servicos.estoque.saldos import variacoes_divergentes
    from plataforma_de_servicos.estoque.saldos_migracao import (
        checar_antes_da_fonte_unica,
    )

    Produto = apps.get_model("produto", "Produto")
    VariacaoProduto = apps.get_model("produto", "VariacaoProduto")
    InventarioSaldo = apps.get_model("inventario", "InventarioSaldo")
    checar_antes_da_fonte_unica(
        variacoes_divergentes(VariacaoProduto, InventarioSaldo),
        produtos_divergentes(Produto, InventarioSaldo),
        produtos_sem_deposito(Produto, InventarioSaldo),
    )


class Migration(migrations.Migration):
    dependencies = [
        ("inventario", "0009_inventariosaldo_constraints"),
        ("produto", "0016_produto_estoque_nao_negativo"),
    ]

    operations = [
        migrations.RunPython(checar, migrations.RunPython.noop),
    ]
