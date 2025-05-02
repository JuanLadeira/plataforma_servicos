import logging

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render

from plataforma_de_servicos.cart.cart import Cart
from plataforma_de_servicos.produto.models.produto_model import Produto

logger = logging.getLogger("django")


def cart_summary(request):
    cart = Cart(request)
    return render(request, "pages/cart-summary.html", {"cart": cart})


def cart_add(request):
    logging.info("Adicionando produto ao carrinho")
    logging.info(request.POST)
    cart = Cart(request)

    if request.POST.get("action") == "post":
        product_id = int(request.POST.get("product_id"))
        product_quantity = int(request.POST.get("product_quantity"))

        product = get_object_or_404(Produto, id=product_id)

        cart.add(product=product, product_qty=product_quantity)

        cart_quantity = cart.__len__()  # noqa: PLC2801

        return JsonResponse({"qty": cart_quantity})
    return None


def cart_delete(request):
    cart = Cart(request)

    if request.POST.get("action") == "post":
        product_id = int(request.POST.get("product_id"))
        cart.delete(product=product_id)

        cart_total = cart.get_total()
        return JsonResponse({"total": cart_total})
    return None


def cart_update(request):
    cart = Cart(request)
    if request.POST.get("action") == "post":

        product_id = int(request.POST.get("product_id"))
        product_quantity = int(request.POST.get("product_quantity"))

        cart.update(product=product_id, qty=product_quantity)

        cart_quantity = cart.__len__()  # noqa: PLC2801

        cart_total = cart.get_total()

        return JsonResponse({"qty": cart_quantity, "total": cart_total})
    return None
