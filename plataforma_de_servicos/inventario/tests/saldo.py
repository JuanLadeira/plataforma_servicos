"""Dar saldo a produto ou variação em testes.

O estoque de Produto e VariacaoProduto é derivado do InventarioSaldo por trigger (issue #144),
então os testes não gravam ``estoque`` direto: criam saldo num depósito.
"""

from django.db.models import F


def deposito_de_teste(empresa):
    from plataforma_de_servicos.inventario.models import Inventario

    inventario, _ = Inventario.objects.get_or_create(
        empresa=empresa,
        nome="Depósito de teste",
        defaults={"is_ativo": True},
    )
    return inventario


def dar_saldo(alvo, quantidade, inventario=None):
    """Soma ``quantidade`` ao saldo de ``alvo`` (Produto ou VariacaoProduto) no depósito.

    Sem depósito, usa o "Depósito de teste" da empresa do produto. Atualiza ``alvo.estoque``
    (e o do produto, se ``alvo`` for variação) com o valor que o trigger calculou.
    """
    from plataforma_de_servicos.inventario.models import InventarioSaldo
    from plataforma_de_servicos.produto.models.atributos import VariacaoProduto

    variacao = alvo if isinstance(alvo, VariacaoProduto) else None
    produto = variacao.produto if variacao else alvo
    inventario = inventario or deposito_de_teste(produto.empresa)
    saldo, criado = InventarioSaldo.objects.get_or_create(
        inventario=inventario,
        produto=produto,
        variacao=variacao,
        defaults={"quantidade": quantidade},
    )
    if not criado:
        InventarioSaldo.objects.filter(pk=saldo.pk).update(
            quantidade=F("quantidade") + quantidade
        )
    alvo.refresh_from_db(fields=["estoque"])
    if variacao is not None:
        produto.refresh_from_db(fields=["estoque"])
    return saldo
