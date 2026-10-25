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


def checar_antes_da_fonte_unica(variacoes, produtos, sem_deposito, limite=20):
    """Interrompe a migration da fonte única de saldo listando as cópias que não batem com os depósitos."""
    linhas = [
        f"variação #{v.pk}: estoque={v.estoque} depósitos={v.total_depositos}"
        for v in list(variacoes[:limite])
    ]
    linhas += [
        f"produto #{p.pk}: estoque={p.estoque} depósitos={p.total_depositos}"
        for p in list(produtos[:limite])
    ]
    linhas += [
        f"produto #{p.pk}: estoque={p.estoque} sem nenhum depósito"
        for p in list(sem_deposito[:limite])
    ]
    if linhas:
        raise RuntimeError(
            "O estoque de produto e variação vai passar a ser a soma dos depósitos, "
            "mas estes registros não batem:\n"
            + "\n".join(linhas)
            + "\nRode `python manage.py verificar_saldos --corrigir` e migre de novo.",
        )
