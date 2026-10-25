from types import SimpleNamespace

from plataforma_de_servicos.estoque.exceptions import InventarioSaldoInsuficienteError
from plataforma_de_servicos.inventario.exceptions import InventarioPadraoAusenteError


def test_inventario_saldo_insuficiente_mostra_deposito_e_saldo():
    saldo = SimpleNamespace(inventario="Loja Centro", quantidade=2)
    erro = InventarioSaldoInsuficienteError(saldo, quantidade=5, item="Camiseta - P")
    assert "Loja Centro" in str(erro)
    assert "5" in str(erro)
    assert "2" in str(erro)


def test_inventario_padrao_ausente_cita_a_empresa():
    erro = InventarioPadraoAusenteError(SimpleNamespace(nome="Empresa A"))
    assert "Empresa A" in str(erro)
