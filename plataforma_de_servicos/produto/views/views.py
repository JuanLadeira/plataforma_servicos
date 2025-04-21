
import logging

from django.shortcuts import get_object_or_404
from django.shortcuts import render

from plataforma_de_servicos.produto.models.categoria_model import Categoria
from plataforma_de_servicos.produto.models.produto_model import Produto

logger = logging.getLogger("django")


def home(request):
    # Obter o ID da categoria do parâmetro GET (se existir)
    # Filtrar produtos por categoria, se fornecido
    if category_id := request.GET.get("category"):
        produtos = Produto.objects.filter(categoria__id=category_id).prefetch_related("images")
    else:
        produtos = Produto.objects.all().prefetch_related("images")

    if search := request.GET.get("search"):
        produtos = produtos.filter(produto__icontains=search)

        logger.info("Nenhum filtro de categoria aplicado, exibindo todos os produtos")
# Verificar se a requisição é feita via HTMX
    # Preparar os produtos com imagens e estoque > 0
    produtos_with_images = [
        {
            "produto": produto.produto,
            "imagem": produto.get_image(),
            "slug": produto.slug,
            "categoria": produto.categoria.categoria if produto.categoria else "Sem categoria",
            "preco": produto.preco,
            "estoque": produto.estoque,
        }
        for produto in produtos if produto.estoque > 0
    ]

    # Obter todas as categorias
    categorias = Categoria.objects.all()

    context = {"my_products": produtos_with_images, "categories": categorias}
    # Verificar se a requisição é feita via HTMX
    logger.info(context)
    if request.headers.get("HX-Request"):
        # Retornar apenas o template parcial com os produtos filtrados
        logger.info("Requisição HTMX detectada, retornando apenas o template parcial")

        return render(request, "pages/partials/product_list_partial.html", context)

    logger.info("Renderizando a página inicial com produtos e categorias")
    # Caso contrário, renderizar a página completa

    return render(request, "pages/home.html", context)


def list_category(request, category_slug=None):

    category = get_object_or_404(Categoria, slug=category_slug)

    produtos = Produto.objects.filter(category=category)

    return render(request, "store/list-category.html", {"category": category, "Produtos": produtos})


def produto_detail(request, produto_slug):

    produto = get_object_or_404(Produto, slug=produto_slug)

    context = {"produto": produto}

    return render(request, "pages/produto-detail.html", context)
