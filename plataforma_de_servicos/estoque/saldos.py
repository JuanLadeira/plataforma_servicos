"""Consultas e correção de saldos de estoque.

Usado pelo comando ``verificar_saldos`` e pelas migrations que criam as constraints de saldo.
As funções recebem as classes de model como parâmetro para funcionar também com os models
históricos das migrations.
"""

from django.db import connection
from django.db import transaction
from django.db.models import Count
from django.db.models import F
from django.db.models import IntegerField
from django.db.models import OuterRef
from django.db.models import Q
from django.db.models import Subquery
from django.db.models import Sum
from django.db.models import Value
from django.db.models.functions import Coalesce


def _soma_depositos(InventarioSaldo, campo):  # noqa: N803
    """Soma de InventarioSaldo.quantidade agrupada pelo campo (produto ou variacao) da linha externa."""
    return Coalesce(
        Subquery(
            InventarioSaldo.objects.filter(**{campo: OuterRef("pk")})
            .values(campo)
            .annotate(t=Sum("quantidade"))
            .values("t")[:1],
            output_field=IntegerField(),
        ),
        Value(0),
    )


def saldos_negativos(InventarioSaldo, empresa=None):  # noqa: N803
    qs = InventarioSaldo.objects.filter(quantidade__lt=0)
    if empresa:
        qs = qs.filter(inventario__empresa__slug=empresa)
    return qs.order_by("pk")


def produtos_negativos(Produto, empresa=None):  # noqa: N803
    qs = Produto.objects.filter(estoque__lt=0)
    if empresa:
        qs = qs.filter(empresa__slug=empresa)
    return qs.order_by("pk")


def saldos_duplicados(InventarioSaldo, empresa=None):  # noqa: N803
    qs = InventarioSaldo.objects.all()
    if empresa:
        qs = qs.filter(inventario__empresa__slug=empresa)
    return (
        qs.values("inventario_id", "produto_id", "variacao_id")
        .annotate(n=Count("id"))
        .filter(n__gt=1)
        .order_by("inventario_id", "produto_id", "variacao_id")
    )


def variacoes_divergentes(VariacaoProduto, InventarioSaldo, empresa=None):  # noqa: N803
    qs = VariacaoProduto.objects.filter(inventariosaldo__isnull=False)
    if empresa:
        qs = qs.filter(produto__empresa__slug=empresa)
    return (
        qs.distinct()
        .annotate(total_depositos=_soma_depositos(InventarioSaldo, "variacao"))
        .exclude(estoque=F("total_depositos"))
        .order_by("pk")
    )


def produtos_divergentes(Produto, InventarioSaldo, empresa=None):  # noqa: N803
    qs = Produto.objects.filter(inventariosaldo__isnull=False)
    if empresa:
        qs = qs.filter(empresa__slug=empresa)
    return (
        qs.distinct()
        .annotate(total_depositos=_soma_depositos(InventarioSaldo, "produto"))
        .exclude(estoque=F("total_depositos"))
        .order_by("pk")
    )


def produtos_sem_deposito(Produto, InventarioSaldo, empresa=None):  # noqa: N803
    """Produtos com estoque (no produto ou em alguma variação) e nenhum saldo de depósito.

    Não dá para recalcular pela soma; ``corrigir`` dá entrada no depósito padrão da empresa.
    """
    qs = Produto.objects.filter(inventariosaldo__isnull=True).filter(
        Q(estoque__gt=0) | Q(variacoes__estoque__gt=0),
    )
    if empresa:
        qs = qs.filter(empresa__slug=empresa)
    return qs.distinct().order_by("pk")


def _liberar_gravacao_de_estoque(*, ligar):
    """Liga ou desliga, só na transação atual, a gravação direta de estoque de produto e variação."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.sync_saldo', %s, true)", ["on" if ligar else "off"])


@transaction.atomic
def corrigir(Produto, VariacaoProduto, InventarioSaldo, empresa=None):  # noqa: N803
    """Junta saldos duplicados e recalcula produto e variação pela soma dos depósitos.

    Não altera saldo negativo de depósito (corrige-se com movimentação de entrada, que deixa histórico)
    nem produtos sem nenhum depósito.
    """
    for dup in saldos_duplicados(InventarioSaldo, empresa):
        linhas = list(
            InventarioSaldo.objects.select_for_update()
            .filter(
                inventario_id=dup["inventario_id"],
                produto_id=dup["produto_id"],
                variacao_id=dup["variacao_id"],
            )
            .order_by("pk"),
        )
        manter, sobras = linhas[0], linhas[1:]
        manter.quantidade = sum(linha.quantidade for linha in linhas)
        manter.save(update_fields=["quantidade"])
        InventarioSaldo.objects.filter(pk__in=[s.pk for s in sobras]).delete()
    # Com os triggers da fonte única (issue #144) instalados, o banco recusa gravar estoque
    # fora da sincronização; o recálculo pela soma dos depósitos é essa sincronização.
    _liberar_gravacao_de_estoque(ligar=True)
    for v in variacoes_divergentes(VariacaoProduto, InventarioSaldo, empresa):
        VariacaoProduto.objects.filter(pk=v.pk).update(
            estoque=max(v.total_depositos, 0),
        )
    for p in produtos_divergentes(Produto, InventarioSaldo, empresa):
        Produto.objects.filter(pk=p.pk).update(estoque=max(p.total_depositos, 0))
    _liberar_gravacao_de_estoque(ligar=False)
    return dar_entrada_aos_produtos_sem_deposito(empresa)


def dar_entrada_aos_produtos_sem_deposito(empresa=None):
    """Cria, no depósito padrão da empresa, uma entrada com o estoque atual de cada produto sem depósito.

    Assim o número se mantém e fica no histórico, antes de o estoque passar a ser a soma dos
    depósitos (issue #144). Devolve os produtos que ficaram de fora por falta de depósito padrão.
    """
    from plataforma_de_servicos.estoque.choices.movimento import Movimento
    from plataforma_de_servicos.estoque.models import Estoque
    from plataforma_de_servicos.estoque.models import EstoqueItens
    from plataforma_de_servicos.inventario.exceptions import (
        InventarioPadraoAusenteError,
    )
    from plataforma_de_servicos.inventario.models import Inventario
    from plataforma_de_servicos.inventario.models import InventarioSaldo
    from plataforma_de_servicos.produto.models.produto_model import Produto

    sem_padrao = []
    for produto in produtos_sem_deposito(Produto, InventarioSaldo, empresa).prefetch_related("variacoes"):
        try:
            deposito = Inventario.objects.padrao_da_empresa(produto.empresa)
        except InventarioPadraoAusenteError:
            sem_padrao.append(produto)
            continue
        itens = [(v, v.estoque) for v in produto.variacoes.all() if v.estoque > 0]
        resto = (produto.estoque or 0) - sum(q for _, q in itens)
        if resto > 0:
            itens.append((None, resto))
        entrada = Estoque.objects.create(
            empresa=produto.empresa,
            movimento=Movimento.ENTRADA.value,
            inventario_destino=deposito,
            observacao="Ajuste automático: estoque sem depósito antes da fonte única de saldo (#144)",
        )
        for variacao, quantidade in itens:
            EstoqueItens.objects.create(
                estoque=entrada, produto=produto, variacao=variacao, quantidade=quantidade, inventario=deposito,
            )
        entrada.processar()
    return sem_padrao
