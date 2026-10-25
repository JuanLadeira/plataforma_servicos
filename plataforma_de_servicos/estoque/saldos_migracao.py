def checar_antes_das_constraints(negativos, duplicados, limite=20):
    """Interrompe a migration listando os registros que violariam as constraints de saldo."""
    linhas = [f"saldo negativo: {r}" for r in list(negativos[:limite])]
    linhas += [f"saldo duplicado: {r}" for r in list(duplicados[:limite])]
    if linhas:
        raise RuntimeError(
            "Existem saldos que impedem criar as constraints de estoque:\n"
            + "\n".join(linhas)
            + "\nRode `python manage.py verificar_saldos` para ver tudo e "
            "`verificar_saldos --corrigir` ou movimentações de entrada para corrigir.",
        )
