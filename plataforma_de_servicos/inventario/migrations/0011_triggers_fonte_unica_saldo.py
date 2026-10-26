"""Estoque de Produto e VariacaoProduto passa a ser derivado do InventarioSaldo (issue #144).

O SQL fica em inventario/sql/ para ser lido e revisado como SQL.
"""

from pathlib import Path

from django.db import migrations

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


def _sql(nome, apps):
    tabelas = {
        "saldo": apps.get_model("inventario", "InventarioSaldo")._meta.db_table,
        "produto": apps.get_model("produto", "Produto")._meta.db_table,
        "variacao": apps.get_model("produto", "VariacaoProduto")._meta.db_table,
    }
    return (SQL_DIR / nome).read_text(encoding="utf-8").format(**tabelas)


def criar(apps, schema_editor):
    schema_editor.execute(_sql("fonte_unica_saldo.sql", apps), params=None)


def remover(apps, schema_editor):
    schema_editor.execute(_sql("fonte_unica_saldo_reverso.sql", apps), params=None)


class Migration(migrations.Migration):
    dependencies = [
        ("inventario", "0010_checar_saldos_antes_fonte_unica"),
    ]

    operations = [
        migrations.RunPython(criar, remover),
    ]
