"""
Views customizadas para navegação de inventário no admin dos gerentes.

Fluxo de navegação:
    Inventários → Produtos do Inventário → Variações com saldo específico
"""

from django.db.models import Count
from django.db.models import Q
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.inventario.models import InventarioSaldo
from plataforma_de_servicos.produto.models.produto_model import Produto


def get_tenant_from_request(request):
    """Obtém o tenant do request."""
    return getattr(request, "tenant", None)


def inventario_browser_list(request, admin_site):
    """
    Lista todos os inventários com contagem de produtos e variações.
    URL: /gerentes/inventario-browser/
    """
    tenant = get_tenant_from_request(request)

    # Filtra por tenant se disponível
    inventarios = Inventario.objects.all()
    if tenant:
        inventarios = inventarios.filter(empresa=tenant)

    # Anota com contagens de produtos e variações com saldo > 0
    inventarios = inventarios.annotate(
        total_produtos=Count(
            "inventariosaldo__produto",
            filter=Q(inventariosaldo__quantidade__gt=0),
            distinct=True,
        ),
        total_variacoes=Count(
            "inventariosaldo",
            filter=Q(inventariosaldo__quantidade__gt=0),
        ),
        total_itens=Sum(
            "inventariosaldo__quantidade",
            filter=Q(inventariosaldo__quantidade__gt=0),
        ),
    ).order_by("nome")

    # Obtém o contexto base do admin site
    context = {
        **admin_site.each_context(request),
        "title": "Navegador de Inventários",
        "subtitle": "Visualize produtos por inventário",
        "inventarios": inventarios,
        "opts": Inventario._meta,
        "app_label": "inventario",
    }

    return TemplateResponse(
        request,
        "admin/inventario/browser/inventario_list.html",
        context,
    )


def inventario_browser_produtos(request, inventario_id, admin_site):
    """
    Lista produtos de um inventário específico com seus saldos.
    URL: /gerentes/inventario-browser/<inventario_id>/produtos/
    """
    tenant = get_tenant_from_request(request)

    # Obtém o inventário
    inventario_qs = Inventario.objects.all()
    if tenant:
        inventario_qs = inventario_qs.filter(empresa=tenant)

    inventario = get_object_or_404(inventario_qs, pk=inventario_id)

    # Busca produtos que têm saldo neste inventário
    produtos_com_saldo = (
        InventarioSaldo.objects.filter(
            inventario=inventario,
            quantidade__gt=0,
        )
        .values("produto")
        .annotate(
            total_quantidade=Sum("quantidade"),
            total_variacoes=Count("id"),
        )
        .order_by("produto__produto")
    )

    # Busca os objetos Produto completos
    produto_ids = [p["produto"] for p in produtos_com_saldo]
    produtos = Produto.objects.filter(id__in=produto_ids).select_related("categoria")

    # Cria um mapa de estatísticas por produto
    stats_map = {p["produto"]: p for p in produtos_com_saldo}

    # Combina produtos com suas estatísticas
    produtos_list = []
    for produto in produtos:
        stats = stats_map.get(produto.id, {})
        produtos_list.append({
            "produto": produto,
            "total_quantidade": stats.get("total_quantidade", 0),
            "total_variacoes": stats.get("total_variacoes", 0),
        })

    # Ordena por nome do produto
    produtos_list.sort(key=lambda x: x["produto"].produto)

    # Filtro de busca
    search_query = request.GET.get("q", "").strip()
    if search_query:
        produtos_list = [
            p for p in produtos_list
            if search_query.lower() in p["produto"].produto.lower()
            or (p["produto"].categoria and search_query.lower() in p["produto"].categoria.nome.lower())
        ]

    # Obtém o contexto base do admin site
    context = {
        **admin_site.each_context(request),
        "title": f"Produtos em {inventario.nome}",
        "subtitle": f"{len(produtos_list)} produtos com estoque",
        "inventario": inventario,
        "produtos_list": produtos_list,
        "search_query": search_query,
        "opts": Inventario._meta,
        "app_label": "inventario",
    }

    return TemplateResponse(
        request,
        "admin/inventario/browser/produto_list.html",
        context,
    )


def inventario_browser_variacoes(request, inventario_id, produto_id, admin_site):
    """
    Lista variações de um produto com saldos específicos do inventário.
    URL: /gerentes/inventario-browser/<inventario_id>/produtos/<produto_id>/
    """
    tenant = get_tenant_from_request(request)

    # Obtém o inventário
    inventario_qs = Inventario.objects.all()
    if tenant:
        inventario_qs = inventario_qs.filter(empresa=tenant)

    inventario = get_object_or_404(inventario_qs, pk=inventario_id)

    # Obtém o produto
    produto_qs = Produto.objects.all()
    if tenant:
        produto_qs = produto_qs.filter(empresa=tenant)

    produto = get_object_or_404(produto_qs.select_related("categoria"), pk=produto_id)

    # Busca saldos das variações deste produto neste inventário
    saldos = (
        InventarioSaldo.objects.filter(
            inventario=inventario,
            produto=produto,
        )
        .select_related("variacao")
        .prefetch_related("variacao__valores", "variacao__valores__atributo")
        .order_by("variacao__sku")
    )

    # Prepara lista de variações com saldos
    variacoes_list = []
    for saldo in saldos:
        if saldo.variacao:
            valores = ", ".join(
                f"{v.atributo.nome}: {v.valor}"
                for v in saldo.variacao.valores.all()
            )
            variacoes_list.append({
                "variacao": saldo.variacao,
                "sku": saldo.variacao.sku,
                "valores": valores,
                "quantidade": saldo.quantidade,
                "preco": saldo.variacao.preco or produto.preco,
                "atualizado_em": saldo.atualizado_em,
            })
        else:
            # Produto sem variação
            variacoes_list.append({
                "variacao": None,
                "sku": getattr(produto, "sku", None) or "-",
                "valores": "Produto base (sem variação)",
                "quantidade": saldo.quantidade,
                "preco": produto.preco,
                "atualizado_em": saldo.atualizado_em,
            })

    # Calcula totais
    total_quantidade = sum(v["quantidade"] for v in variacoes_list)

    # Filtro de busca
    search_query = request.GET.get("q", "").strip()
    if search_query:
        variacoes_list = [
            v for v in variacoes_list
            if search_query.lower() in v["valores"].lower()
            or search_query.lower() in str(v["sku"]).lower()
        ]

    # Obtém o contexto base do admin site
    context = {
        **admin_site.each_context(request),
        "title": produto.produto,
        "subtitle": f"Estoque em {inventario.nome}",
        "inventario": inventario,
        "produto": produto,
        "variacoes_list": variacoes_list,
        "total_quantidade": total_quantidade,
        "search_query": search_query,
        "opts": Inventario._meta,
        "app_label": "inventario",
    }

    return TemplateResponse(
        request,
        "admin/inventario/browser/variacao_list.html",
        context,
    )
