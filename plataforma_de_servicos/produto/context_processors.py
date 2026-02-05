from django.db.models import Count, Q

from plataforma_de_servicos.produto.models.categoria_model import Categoria


def categories(request):
    # Annotate with variation count for available products with stock
    all_categories = Categoria.objects.annotate(
        produto_count=Count(
            'produtos__variacoes',
            filter=Q(produtos__variacoes__estoque__gt=0, produtos__variacoes__produto__disponivel=True)
        )
    ).order_by('categoria')
    return {"categories": all_categories}
