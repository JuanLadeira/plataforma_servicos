import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from plataforma_de_servicos.estoque.models.proxys.estoque_entrada import EstoqueEntrada
from plataforma_de_servicos.estoque.models.proxys.transferencia import Transferencia
from plataforma_de_servicos.estoque.models.estoque_itens_model import EstoqueItens
from plataforma_de_servicos.inventario.models import Inventario, InventarioSaldo
from plataforma_de_servicos.produto.models import Produto, Categoria

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(email="test@example.com", password="testpassword")


@pytest.fixture
def categoria():
    return Categoria.objects.create(categoria="Test Category")


@pytest.fixture
def produto(categoria):
    return Produto.objects.create(
        produto="Test Product",
        preco=Decimal("10.00"),
        estoque=0,  # Estoque inicial geral é 0
        categoria=categoria,
    )


@pytest.fixture
def inventario_origem():
    return Inventario.objects.create(nome="Inventário Origem")


@pytest.fixture
def inventario_destino():
    return Inventario.objects.create(nome="Inventário Destino")


@pytest.fixture
def entrada_inicial(user, produto, inventario_origem):
    # Cria uma entrada de 10 unidades no inventário de origem
    entrada = EstoqueEntrada.objects.create(
        funcionario=user,
        movimento="e",
        inventario_destino=inventario_origem,
    )
    EstoqueItens.objects.create(
        estoque=entrada,
        produto=produto,
        quantidade=10,
        inventario=inventario_origem
    )
    entrada.processar()
    produto.refresh_from_db()
    return entrada


def test_criar_transferencia_de_estoque(
    user,
    produto,
    inventario_origem,
    inventario_destino,
    entrada_inicial,
):
    """
    Testa a criação e o processamento de uma transferência de estoque,
    verificando se os saldos nos inventários de origem e destino são
    atualizados corretamente.
    """
    # 1. Verificar saldo inicial
    saldo_origem_inicial = InventarioSaldo.objects.get(
        inventario=inventario_origem, produto=produto
    ).quantidade
    assert saldo_origem_inicial == 10
    assert not InventarioSaldo.objects.filter(
        inventario=inventario_destino, produto=produto
    ).exists()

    # 2. Criar a transferência
    transferencia = Transferencia.objects.create(
        funcionario=user,
        movimento="t",
        inventario_origem=inventario_origem,
        inventario_destino=inventario_destino,
        observacao="Transferindo 5 unidades"
    )
    EstoqueItens.objects.create(
        estoque=transferencia,
        produto=produto,
        quantidade=5,
        inventario=inventario_origem # O item sai da origem
    )

    # 3. Processar a transferência
    transferencia.processar()

    # 4. Verificar saldos finais
    saldo_origem_final = InventarioSaldo.objects.get(
        inventario=inventario_origem, produto=produto
    ).quantidade
    saldo_destino_final = InventarioSaldo.objects.get(
        inventario=inventario_destino, produto=produto
    ).quantidade

    assert saldo_origem_final == 5
    assert saldo_destino_final == 5

    # 5. Verificar o estoque global do produto (não deve mudar com transferência)
    produto.refresh_from_db()
    assert produto.estoque == 10


def test_transferencia_sem_inventarios_falha(user, produto):
    """Testa que a validação do modelo impede transferências sem inventários."""
    transferencia = Transferencia(
        funcionario=user,
        movimento="t",
        inventario_origem=None,
        inventario_destino=None,
    )
    with pytest.raises(ValidationError, match="Transferência requer origem e destino"):
        transferencia.full_clean()
