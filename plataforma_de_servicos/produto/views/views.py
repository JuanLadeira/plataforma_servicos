
import logging
from dataclasses import asdict

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.template.context_processors import csrf
from django.views.decorators.http import require_POST

from plataforma_de_servicos.produto.models import VariacaoProduto
from plataforma_de_servicos.produto.models.categoria_model import Categoria
from plataforma_de_servicos.produto.models.produto_model import Produto
from plataforma_de_servicos.produto.services import ProdutoService
from plataforma_de_servicos.produto.services.search_service import ProductSearchService
from plataforma_de_servicos.produto.services.search_service import SearchParams

logger = logging.getLogger("django")


def home(request):
    """
    View principal da vitrine usando ProductSearchService.

    Suporta:
    - Filtro por categoria via query param 'category'
    - Busca textual via query param 'search'
    - Requisições HTMX para atualização parcial
    - Sincronização de filtros ativos e contagem de categorias
    """
    category_id = request.GET.get("category")
    search = request.GET.get("search")

    # Usar o ProductSearchService para busca centralizada
    search_service = ProductSearchService(request.tenant)
    params = SearchParams(
        category_id=category_id,
        search_query=search,
    )
    result = search_service.search(params)

    if search:
        logger.info("Filtro de busca aplicado: %s", search)

    # Prepara as variações para o template (mantém compatibilidade)
    variacoes_vitrine = ProdutoService.preparar_variacoes_para_vitrine(result.variations)

    selected_category = None
    if category_id:
        try:
            selected_category = int(category_id)
        except (ValueError, TypeError):
            pass

    context = {
        "my_variations": variacoes_vitrine,
        "categoria": result.category or result.category_name,
        "selected_category": selected_category,
        # Novos campos do ProductSearchService
        "active_filters": result.active_filters,
        "category_counts": result.category_counts,
        "total_count": result.total_count,
        "search_query": search or "",
    }

    if request.headers.get("HX-Request"):
        logger.info("Requisição HTMX detectada, retornando apenas o template parcial")
        return render(request, "pages/partials/product_list_partial.html", context)

    logger.info("Renderizando a página inicial com produtos e categorias")
    return render(request, "pages/home.html", context)


def categories(request):
    tenant = getattr(request, "tenant", None)
    if tenant:
        all_categories = Categoria.objects.filter(empresa=tenant)
    else:
        all_categories = Categoria.objects.none()
    return {"categories": all_categories}


def produto_detail(request, produto_slug):
    tenant = getattr(request, "tenant", None)

    # Filtra por tenant para evitar vazamento de dados entre empresas
    queryset = Produto.objects.all()
    if tenant:
        queryset = queryset.filter(empresa=tenant)

    produto = get_object_or_404(queryset, slug=produto_slug)

    variacoes = produto.variacoes.prefetch_related("valores__atributo").all()
    atributos = ProdutoService.obter_atributos_variacoes(produto)

    context = {
        "produto": produto,
        "imagens": produto.get_images(),
        "estoque_range": produto.get_stock_range(),
        "atributos": atributos,
        "variacoes": variacoes,
        "tem_variacoes": variacoes.exists(),
    }
    context.update(csrf(request))

    return render(request, "pages/produto-detail.html", context)


def category_search(request):
    search_text = request.POST.get("search")
    tenant = getattr(request, "tenant", None)

    if search_text and tenant:
        results = Categoria.objects.filter(
            categoria__icontains=search_text,
            empresa=tenant
        )
    else:
        results = Categoria.objects.none()

    return render(
        request, "pages/partials/category_results.html", {"categories": results},
    )


@require_POST
def calcular_preco_variacao(request):
    """Endpoint HTMX para calcular preço baseado nos atributos selecionados"""
    produto_id = request.POST.get("produto_id")
    valores_ids = request.POST.getlist("valores[]")
    tenant = getattr(request, "tenant", None)

    if not produto_id:
        return JsonResponse({"error": "Produto não informado"}, status=400)

    # Filtra por tenant para evitar vazamento de dados entre empresas
    queryset = Produto.objects.all()
    if tenant:
        queryset = queryset.filter(empresa=tenant)

    produto = get_object_or_404(queryset, id=produto_id)

    resultado = ProdutoService.calcular_preco_variacao(produto, valores_ids or None)

    return JsonResponse(asdict(resultado))


def variacao_detail(request, sku):
    """
    Exibe os detalhes de uma variação específica de um produto.
    """
    tenant = getattr(request, "tenant", None)

    # Filtra por tenant para evitar vazamento de dados entre empresas
    queryset = VariacaoProduto.objects.select_related("produto__categoria")
    if tenant:
        queryset = queryset.filter(produto__empresa=tenant)

    variacao = get_object_or_404(queryset, sku=sku)
    produto = variacao.produto

    context = {
        "variacao": variacao,
        "produto": produto,
        "imagens": produto.get_images(),
        "atributos": variacao.valores.select_related("atributo"),
    }
    context.update(csrf(request))

    return render(request, "pages/variacao-detail.html", context)
