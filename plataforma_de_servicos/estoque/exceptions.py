class ProdutoSaldoInsuficienteError(Exception):
    def __init__(self, nome_produto, quantidade):
        super().__init__(
            f"""Não é possível
            realizar a saída de {nome_produto}.
            Saldo insuficiente para a
            quantidade {quantidade}""",
        )


class VariacaoSaldoInsuficienteError(Exception):
    def __init__(self, variacao, quantidade):
        super().__init__(
            f"""Não é possível realizar a saída da variação '{variacao}'.
            Saldo insuficiente para a quantidade {quantidade}.
            Estoque atual da variação: {variacao.estoque}""",
        )


class ProtocoloProcessadoError(Exception):
    def __init__(self):
        super().__init__("Já foi dado baixa nessa entrega.")


class InventarioSaldoInsuficienteError(Exception):
    def __init__(self, saldo, quantidade, item):
        super().__init__(
            f"Saldo insuficiente de '{item}' no depósito {getattr(saldo.inventario, 'nome', saldo.inventario)}: "
            f"saldo {saldo.quantidade}, solicitado {quantidade}.",
        )
