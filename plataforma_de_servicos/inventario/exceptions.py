class InventarioPadraoAusenteError(Exception):
    def __init__(self, empresa):
        if empresa is None:
            super().__init__(
                "Registro sem empresa: não há depósito padrão para dar baixa."
            )
            return
        super().__init__(
            f"A empresa {empresa.nome} não tem depósito padrão. "
            "Marque um inventário ativo como padrão no portal de gerentes.",
        )
