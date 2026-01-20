
import logging

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.template.context_processors import csrf
from django.views.decorators.http import require_POST

from plataforma_de_servicos.produto.models.categoria_model import Categoria
from plataforma_de_servicos.produto.models.produto_model import Produto

logger = logging.getLogger("django")


def home(request):
    # Obter o ID da categoria do parâmetro GET (se existir)
    # Filtrar produtos por categoria, se fornecido
    if category_id := request.GET.get("category"):
        produtos = Produto.objects.filter(categoria__id=category_id).prefetch_related("images")
        categoria = Categoria.objects.filter(id=category_id).first()
    else:
        produtos = Produto.objects.all().prefetch_related("images")
        categoria = "Todos os produtos"
    if search := request.GET.get("search"):
        produtos = produtos.filter(produto__icontains=search)

        logger.info("Nenhum filtro de categoria aplicado, exibindo todos os produtos")
# Verificar se a requisição é feita via HTMX
    # Preparar os produtos com imagens e estoque > 0
    produtos_with_images = [
        {
            "id": produto.id,
            "produto": produto.produto,
            "imagem": produto.get_image(),
            "slug": produto.slug,
            "categoria": produto.categoria.categoria if produto.categoria else "Sem categoria",
            "preco": produto.preco,
            "estoque": produto.estoque,
            "url": produto.get_absolute_url(),
        }
        for produto in produtos if produto.estoque > 0
    ]

    context = {"my_products": produtos_with_images, "categoria": categoria}
    # Verificar se a requisição é feita via HTMX
    logger.info(context)
    if request.headers.get("HX-Request"):
        # Retornar apenas o template parcial com os produtos filtrados
        logger.info("Requisição HTMX detectada, retornando apenas o template parcial")

        return render(request, "pages/partials/product_list_partial.html", context)

    logger.info("Renderizando a página inicial com produtos e categorias")
    # Caso contrário, renderizar a página completa

    return render(request, "pages/home.html", context)


def categories(request):
    all_categories = Categoria.objects.all()
    return {"categories": all_categories}


def produto_detail(request, produto_slug):
    produto = get_object_or_404(Produto, slug=produto_slug)

    # Buscar variações do produto
    variacoes = produto.variacoes.prefetch_related('valores__atributo').all()

    # Extrair atributos únicos das variações
    atributos_dict = {}
    for variacao in variacoes:
        for valor in variacao.valores.all():
            atributo = valor.atributo
            if atributo.id not in atributos_dict:
                atributos_dict[atributo.id] = {
                    'atributo': atributo,
                    'valores': set()
                }
            atributos_dict[atributo.id]['valores'].add(valor)

    # Converter para lista ordenada
    atributos = [
        {
            'atributo': data['atributo'],
            'valores': sorted(data['valores'], key=lambda v: v.valor)
        }
        for data in atributos_dict.values()
    ]

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

    # Realiza a busca case-insensitive e retorna os resultados
    if search_text:
        results = Categoria.objects.filter(categoria__icontains=search_text)
    else:
        results = Categoria.objects.none()

    return render(
        request, "pages/partials/category_results.html", {"categories": results}
    )


@require_POST
def calcular_preco_variacao(request):
    """Endpoint HTMX para calcular preço baseado nos atributos selecionados"""
    produto_id = request.POST.get("produto_id")
    valores_ids = request.POST.getlist("valores[]")

    if not produto_id:
        return JsonResponse({"error": "Produto não informado"}, status=400)

    produto = get_object_or_404(Produto, id=produto_id)

    # Se não houver valores selecionados, retornar preço base
    if not valores_ids:
        return JsonResponse({
            "preco": str(produto.preco) if produto.preco else "0",
            "preco_formatado": f"R$ {produto.preco:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if produto.preco else "R$ 0,00",
            "estoque": produto.estoque or 0,
            "variation_id": None,
            "disponivel": (produto.estoque or 0) > 0,
        })

    # Buscar variação que corresponde aos valores selecionados
    variacoes = produto.variacoes.prefetch_related('valores').all()

    variacao_encontrada = None
    valores_ids_set = set(map(int, valores_ids))

    for variacao in variacoes:
        variacao_valores_ids = set(variacao.valores.values_list('id', flat=True))
        if variacao_valores_ids == valores_ids_set:
            variacao_encontrada = variacao
            break

    if variacao_encontrada:
        preco_final = variacao_encontrada.calcular_preco_final()
        return JsonResponse({
            "preco": str(preco_final),
            "preco_formatado": f"R$ {preco_final:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            "estoque": variacao_encontrada.estoque,
            "variation_id": variacao_encontrada.id,
            "disponivel": variacao_encontrada.estoque > 0,
        })
    else:
        # Sem variação específica, usar preço base
        return JsonResponse({
            "preco": str(produto.preco) if produto.preco else "0",
            "preco_formatado": f"R$ {produto.preco:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if produto.preco else "R$ 0,00",
            "estoque": produto.estoque or 0,
            "variation_id": None,
            "disponivel": (produto.estoque or 0) > 0,
            "combinacao_invalida": True,
        })
