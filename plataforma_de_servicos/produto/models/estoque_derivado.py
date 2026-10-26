"""Estoque de Produto e VariacaoProduto derivado do InventarioSaldo.

A coluna ``estoque`` é mantida por um trigger do Postgres a partir da soma dos
``InventarioSaldo`` (migration ``inventario/0011_triggers_fonte_unica_saldo``).
O banco recusa qualquer outra gravação nela; ajuste de saldo é feito por movimentação.
"""


class EstoqueDerivadoMixin:
    """Um ``save()`` comum de instância existente não regrava ``estoque``.

    Sem isso, salvar uma instância carregada antes de uma movimentação tentaria
    gravar o valor velho e o trigger de guarda recusaria. Quem passa
    ``update_fields`` explicitamente continua no controle.
    """

    def save(self, *args, **kwargs):
        if (
            not self._state.adding
            and kwargs.get("update_fields") is None
            and not kwargs.get("force_insert")
        ):
            kwargs["update_fields"] = [
                f.name
                for f in self._meta.concrete_fields
                if not f.primary_key and f.name != "estoque"
            ]
        super().save(*args, **kwargs)
