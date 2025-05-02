from plataforma_de_servicos.produto.models.categoria_model import Categoria


def categories(request):
    all_categories = Categoria.objects.all()
    return {"categories": all_categories}
