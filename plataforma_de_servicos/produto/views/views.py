
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

logger = logging.getLogger("django")


def home(request):
    category_id = request.GET.get("category")
    search = request.GET.get("search")

    # Use the old service methods for products
    produtos, categoria = ProdutoService.listar_produtos_vitrine(
        category_id=category_id,
        search=search,
    )

    if search:
        logger.info("Filtro de busca aplicado: %s", search)

    # Prepare products for the template
    produtos_vitrine = ProdutoService.preparar_produtos_para_vitrine(produtos)

    selected_category = None
    if category_id:
        try:
            selected_category = int(category_id)
        except (ValueError, TypeError):
            pass

    context = {
        "my_products": produtos_vitrine,
        "categoria": categoria,
        "selected_category": selected_category,
    }

    if request.headers.get("HX-Request"):
        logger.info("Requisição HTMX detectada, retornando apenas o template parcial")
        return render(request, "pages/partials/product_list_partial.html", context)

    logger.info("Renderizando a página inicial com produtos e categorias")
    return render(request, "pages/home.html", context)


def categories(request):
    all_categories = Categoria.objects.all()
    return {"categories": all_categories}


def produto_detail(request, produto_slug):
    produto = get_object_or_404(Produto, slug=produto_slug)

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

    if search_text:
        results = Categoria.objects.filter(categoria__icontains=search_text)
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

    if not produto_id:
        return JsonResponse({"error": "Produto não informado"}, status=400)

    produto = get_object_or_404(Produto, id=produto_id)

    resultado = ProdutoService.calcular_preco_variacao(produto, valores_ids or None)

    return JsonResponse(asdict(resultado))


def variacao_detail(request, sku):
    """
    Exibe os detalhes de uma variação específica de um produto.
    """
    variacao = get_object_or_404(
        VariacaoProduto.objects.select_related('produto__categoria'),
        sku=sku
    )
    produto = variacao.produto

    context = {
        "variacao": variacao,
        "produto": produto,
        "imagens": produto.get_images(),
        "atributos": variacao.valores.select_related('atributo'),
    }
    context.update(csrf(request))

    return render(request, "pages/variacao-detail.html", context)
