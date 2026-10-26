import pytest
from django.db import connection


@pytest.fixture
def sem_constraints_de_saldo(db):
    """Remove, só dentro do teste, as constraints de unicidade e de saldo não negativo.

    Serve para simular dados antigos (negativos ou duplicados) que o banco já não aceita.
    O DDL roda na transação do teste e é desfeito no rollback.
    """
    with connection.cursor() as cursor:
        for tabela in ("inventario_inventariosaldo", "produto_produto"):
            cursor.execute(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = %s::regclass AND contype IN ('u', 'c')",
                [tabela],
            )
            for (nome,) in cursor.fetchall():
                cursor.execute(f'ALTER TABLE {tabela} DROP CONSTRAINT "{nome}"')


@pytest.fixture
def sem_trigger_de_saldo(db):
    """Remove, só dentro do teste, os triggers da fonte única de saldo (issue #144).

    Serve para simular dados de antes da migration, quando produto e variação guardavam
    cópias que podiam divergir dos depósitos. O DDL é desfeito no rollback do teste.
    """
    with connection.cursor() as cursor:
        cursor.execute("DROP TRIGGER sincronizar_estoque_saldo ON inventario_inventariosaldo")
        cursor.execute("DROP TRIGGER guardar_estoque_derivado ON produto_produto")
        cursor.execute("DROP TRIGGER guardar_estoque_derivado ON produto_variacaoproduto")

