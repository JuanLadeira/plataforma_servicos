from django.db.models import Count, Q

from plataforma_de_servicos.produto.models.categoria_model import Categoria


def categories(request):
    """
    Context processor que retorna categorias filtradas por tenant.
    Usado no sidebar para exibir categorias com contagem de produtos disponíveis.
    """
    tenant = getattr(request, "tenant", None)

    if not tenant:
        return {"categories": Categoria.objects.none()}

    # Filtra categorias por empresa e anota com contagem de variações disponíveis
    all_categories = Categoria.objects.filter(
        empresa=tenant
    ).annotate(
        produto_count=Count(
            'produtos__variacoes',
            filter=Q(
                produtos__variacoes__estoque__gt=0,
                produtos__variacoes__produto__disponivel=True,
                produtos__empresa=tenant
            )
        )
    ).order_by('categoria')

    return {"categories": all_categories}
