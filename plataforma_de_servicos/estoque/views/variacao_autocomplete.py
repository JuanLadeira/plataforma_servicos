"""
Autocomplete customizado para variações que inclui o estoque.
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from plataforma_de_servicos.produto.models import VariacaoProduto


@require_GET
@staff_member_required
def variacao_autocomplete(request):
    """
    View de autocomplete que retorna variações com estoque incluso.
    O select2 recebe dados extras que podem ser usados pelo JavaScript.
    """
    term = request.GET.get("term", "")
    page = int(request.GET.get("page", 1))
    page_size = 20

    # Queryset base
    qs = VariacaoProduto.objects.select_related("produto").prefetch_related("valores")

    # Filtra por tenant se disponível
    tenant = getattr(request, "tenant", None)
    if tenant:
        qs = qs.filter(produto__empresa=tenant)

    # Filtra por termo de busca
    if term:
        from django.db.models import Q
        qs = qs.filter(
            Q(sku__icontains=term) |
            Q(produto__produto__icontains=term) |
            Q(valores__valor__icontains=term)
        ).distinct()

    # Paginação
    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    variacoes = qs[start:end]

    # Montar resultados com estoque
    results = []
    for variacao in variacoes:
        valores = ", ".join(v.valor for v in variacao.valores.all())
        text = f"{variacao.produto.produto} - {valores}" if valores else variacao.produto.produto

        results.append({
            "id": variacao.pk,
            "text": text,
            "estoque": variacao.estoque,  # Dado extra para o JavaScript!
            "sku": variacao.sku,
        })

    return JsonResponse({
        "results": results,
        "pagination": {"more": end < total},
    })
