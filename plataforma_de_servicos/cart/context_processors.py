
from plataforma_de_servicos.cart.cart import Cart


def cart(request):
    return {"cart": Cart(request)}
