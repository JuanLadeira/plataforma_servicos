import json
import logging

from django.contrib import messages
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse

from plataforma_de_servicos.cart.cart import Cart
from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.produto.models import VariacaoProduto

logger = logging.getLogger("django")


def _render_cart_badge(request, cart):
    """Renderiza o badge do carrinho para atualização via HTMX."""
    return render_to_string(
        "pages/partials/cart_badge.html",
        {"cart": cart},
        request=request,
    )


def _render_cart_offcanvas(request, cart):
    """Renderiza o conteúdo do mini-carrinho (offcanvas)."""
    from django.middleware.csrf import get_token
    return render_to_string(
        "pages/partials/cart_offcanvas.html",
        {"cart": cart, "csrf_token": get_token(request)},
        request=request,
    )


def cart_mini(request):
    """Retorna o HTML do mini-carrinho para HTMX."""
    cart = Cart(request)
    return HttpResponse(_render_cart_offcanvas(request, cart))


def cart_summary(request):
    cart = Cart(request)
    context = {
        "cart": cart,
    }
    return render(request, "pages/cart-summary.html", context)


def cart_add(request):
    cart = Cart(request)
    if request.POST.get("action") == "post":
        product_id = request.POST.get("product_id")
        variation_id = request.POST.get("variation_id")
        product_quantity = int(request.POST.get("product_quantity", 1))
        no_redirect = request.POST.get("no_redirect")  # Para requisições da home

        if variation_id:
            variation = get_object_or_404(VariacaoProduto, id=variation_id)
            produto = variation.produto
            estoque_disponivel = variation.estoque
            produto_nome = f"{produto.produto} ({variation})"
        else:
            produto = get_object_or_404(Produto, id=product_id)
            estoque_disponivel = produto.estoque
            produto_nome = produto.produto
            variation = None  # Para uso no método add_product

        cart_key = str(variation_id) if variation_id else f"produto_{product_id}"
        quantidade_no_carrinho = cart.cart.get(cart_key, {}).get("qty", 0)
        quantidade_total_solicitada = quantidade_no_carrinho + product_quantity

        if quantidade_total_solicitada > estoque_disponivel:
            error_msg = f"Estoque insuficiente para {produto_nome}. Disponível: {estoque_disponivel}."
            messages.error(request, error_msg)
            if request.headers.get("HX-Request"):
                if no_redirect:
                    # Retornar HTML para a home - badge + toast de erro
                    response = HttpResponse(_render_cart_badge(request, cart))
                    response["HX-Trigger"] = json.dumps({
                        "showToast": {"message": error_msg, "type": "error"},
                    })
                    return response
                # Retornar JSON para o handler do produto-detail.html
                return JsonResponse({
                    "error": True,
                    "message": error_msg,
                    "redirect": reverse("cart:cart-summary"),
                })
            return redirect("cart:cart-summary")

        if variation:
            cart.add(variation=variation, product_qty=product_quantity)
        else:
            cart.add_product(produto=produto, product_qty=product_quantity)

        success_msg = f"{produto_nome} adicionado ao carrinho!"
        messages.success(request, success_msg)

        if request.headers.get("HX-Request"):
            if no_redirect:
                # Retornar HTML para a home - badge + trigger para abrir offcanvas
                response = HttpResponse(_render_cart_badge(request, cart))
                response["HX-Trigger"] = json.dumps({
                    "showToast": {"message": success_msg, "type": "success"},
                    "openCartOffcanvas": True,
                })
                return response
            # Retornar JSON para o handler do produto-detail.html
            return JsonResponse({
                "success": True,
                "message": success_msg,
                "redirect": reverse("cart:cart-summary"),
                "qty": len(cart),
            })

        return redirect("cart:cart-summary")

    return JsonResponse({"error": "Invalid request"}, status=400)


def cart_delete(request):
    cart = Cart(request)
    if request.POST.get("action") == "post":
        variation_id = request.POST.get("variation_id")
        cart.delete(variation=variation_id)

        cart_quantity = len(cart)
        cart_total = cart.get_total()
        messages.success(request, "Item removido do carrinho com sucesso!")
        return JsonResponse({
            "qty": cart_quantity,
            "total": f"{cart_total:.2f}",
        })
    return JsonResponse({"error": "Invalid request"}, status=400)


def cart_delete_mini(request):
    """Remove item do carrinho e retorna o offcanvas atualizado."""
    cart = Cart(request)
    if request.POST.get("action") == "post":
        variation_id = request.POST.get("variation_id")
        cart.delete(variation=variation_id)

        # Retorna o offcanvas atualizado com toast
        response = HttpResponse(_render_cart_offcanvas(request, cart))
        response["HX-Trigger"] = json.dumps({
            "showToast": {
                "message": "Item removido do carrinho!",
                "type": "success",
            },
        })
        return response
    return JsonResponse({"error": "Invalid request"}, status=400)


def cart_update(request):
    cart = Cart(request)
    if request.POST.get("action") == "post":
        variation_id = request.POST.get("variation_id")
        product_quantity = int(request.POST.get("product_quantity"))

        # Validar quantidade máxima baseada no estoque
        if variation_id.startswith("produto_"):
            produto_id = int(variation_id.replace("produto_", ""))
            produto = get_object_or_404(Produto, id=produto_id)
            max_estoque = produto.estoque
            preco_unitario = produto.preco
        else:
            variation = get_object_or_404(VariacaoProduto, id=variation_id)
            max_estoque = variation.estoque
            preco_unitario = variation.calcular_preco_final()

        # Limitar quantidade ao estoque disponível
        if product_quantity > max_estoque:
            return JsonResponse({
                "error": f"Quantidade máxima disponível: {max_estoque}",
            }, status=400)

        if product_quantity < 1:
            return JsonResponse({
                "error": "Quantidade mínima: 1",
            }, status=400)

        cart.update(variation=variation_id, qty=product_quantity)

        # Calcular total do item
        item_total = preco_unitario * product_quantity

        cart_quantity = len(cart)
        cart_total = cart.get_total()
        messages.success(request, "Carrinho atualizado com sucesso!")
        return JsonResponse({
            "qty": cart_quantity,
            "total": f"{cart_total:.2f}",
            "item_total": f"{item_total:.2f}",
        })
    return JsonResponse({"error": "Invalid request"}, status=400)
