import logging

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import render

from plataforma_de_servicos.cart.cart import Cart
from plataforma_de_servicos.produto.models import VariacaoProduto

logger = logging.getLogger("django")


def cart_summary(request):
    cart = Cart(request)
    context = {
        "cart": cart,
    }
    return render(request, "pages/cart-summary.html", context)


def cart_add(request):
    cart = Cart(request)
    if request.POST.get("action") == "post":
        variation_id = int(request.POST.get("variation_id"))
        product_quantity = int(request.POST.get("product_quantity"))

        variation = get_object_or_404(VariacaoProduto, id=variation_id)

        cart.add(variation=variation, product_qty=product_quantity)
        cart_quantity = len(cart)
        messages.success(request, f"{variation.produto.produto} adicionado ao carrinho com sucesso!")
        return JsonResponse({"qty": cart_quantity})
    return JsonResponse({"error": "Invalid request"}, status=400)


def cart_delete(request):
    cart = Cart(request)
    if request.POST.get("action") == "post":
        variation_id = int(request.POST.get("variation_id"))
        cart.delete(variation=variation_id)

        cart_total = cart.get_total()
        messages.success(request, "Item removido do carrinho com sucesso!")
        return JsonResponse({"total": cart_total})
    return JsonResponse({"error": "Invalid request"}, status=400)


def cart_update(request):
    cart = Cart(request)
    if request.POST.get("action") == "post":
        variation_id = int(request.POST.get("variation_id"))
        product_quantity = int(request.POST.get("product_quantity"))

        cart.update(variation=variation_id, qty=product_quantity)

        cart_quantity = len(cart)
        cart_total = cart.get_total()
        messages.success(request, "Carrinho atualizado com sucesso!")
        return JsonResponse({"qty": cart_quantity, "total": cart_total})
    return JsonResponse({"error": "Invalid request"}, status=400)