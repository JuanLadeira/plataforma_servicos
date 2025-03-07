class ProdutoSaldoInsuficienteError(Exception):
    def __init__(self, nome_produto, quantidade):
        super().__init__(
            f"""Não é possível
            realizar a saída de {nome_produto}.
            Saldo insuficiente para a
            quantidade {quantidade}""",
        )


class ProtocoloProcessadoError(Exception):
    def __init__(self):
        super().__init__("Já foi dado baixa nessa entrega.")
