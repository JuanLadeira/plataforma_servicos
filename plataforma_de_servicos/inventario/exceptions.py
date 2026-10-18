class InventarioPadraoAusenteError(Exception):
    def __init__(self, empresa):
        super().__init__(
            f"A empresa {empresa.nome} não tem depósito padrão. "
            "Marque um inventário ativo como padrão no portal de gerentes.",
        )
