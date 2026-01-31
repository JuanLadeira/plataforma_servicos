from django.db.models import Count, Q

from plataforma_de_servicos.produto.models.categoria_model import Categoria


def categories(request):
    # Annotate with product count (only available products with stock > 0)
    all_categories = Categoria.objects.annotate(
        produto_count=Count('produtos', filter=Q(produtos__estoque__gt=0, produtos__disponivel=True))
    ).order_by('categoria')
    return {"categories": all_categories}
