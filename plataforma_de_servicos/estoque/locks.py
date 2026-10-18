"""Travas de saldo em ordem fixa.

Toda transação que altera saldo de estoque trava as linhas pela mesma ordem:

1. a movimentação (``Estoque``), feita por quem chama;
2. ``InventarioSaldo``, por (inventario_id, produto_id, variacao_id);
3. ``VariacaoProduto``, por pk;
4. ``Produto``, por pk.

A ordem fixa impede deadlock entre duas operações sobre os mesmos itens.
"""

from dataclasses import dataclass
from dataclasses import field

from django.db import IntegrityError
from django.db import transaction

from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.produto.models.atributos import VariacaoProduto
from plataforma_de_servicos.produto.models.produto_model import Produto


@dataclass
class Travas:
    saldos: dict = field(
        default_factory=dict
    )  # (inventario_id, produto_id, variacao_id) -> InventarioSaldo
    variacoes: dict = field(default_factory=dict)  # pk -> VariacaoProduto
    produtos: dict = field(default_factory=dict)  # pk -> Produto


def inventarios_do_movimento(estoque):
    if estoque.movimento == Movimento.ENTRADA.value:
        return [estoque.inventario_destino_id]
    if estoque.movimento == Movimento.SAIDA.value:
        return [estoque.inventario_origem_id]
    return [estoque.inventario_origem_id, estoque.inventario_destino_id]


def _travar_ou_criar_saldo(inventario_id, produto_id, variacao_id):
    filtro = {
        "inventario_id": inventario_id,
        "produto_id": produto_id,
        "variacao_id": variacao_id,
    }
    try:
        return InventarioSaldo.objects.select_for_update().get(**filtro)
    except InventarioSaldo.DoesNotExist:
        try:
            with transaction.atomic():
                return InventarioSaldo.objects.create(quantidade=0, **filtro)
        except IntegrityError:
            # Outra transação criou o mesmo saldo no meio do caminho.
            return InventarioSaldo.objects.select_for_update().get(**filtro)


def travar_saldos(estoque, itens):
    """Trava, em ordem fixa, todas as linhas de saldo tocadas pela movimentação.

    Precisa rodar dentro de transaction.atomic(), depois de travar a própria movimentação.
    Itens repetidos compartilham a mesma instância travada.
    """
    travas = Travas()
    inventarios = [i for i in inventarios_do_movimento(estoque) if i is not None]
    chaves = sorted(
        {(inv, it.produto_id, it.variacao_id) for it in itens for inv in inventarios},
        key=lambda c: (c[0], c[1], c[2] or 0),
    )
    for chave in chaves:
        travas.saldos[chave] = _travar_ou_criar_saldo(*chave)

    ids_var = sorted({it.variacao_id for it in itens if it.variacao_id})
    travas.variacoes = {
        v.pk: v
        for v in VariacaoProduto.objects.select_for_update()
        .filter(pk__in=ids_var)
        .order_by("pk")
    }

    ids_prod = sorted({it.produto_id for it in itens})
    travas.produtos = {
        p.pk: p
        for p in Produto.objects.select_for_update()
        .filter(pk__in=ids_prod)
        .order_by("pk")
    }
    return travas
