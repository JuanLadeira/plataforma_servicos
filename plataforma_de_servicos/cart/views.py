"""
Cart Views - Controladores para o carrinho de compras.

Segue o padrão Model -> Service -> View.
Toda a lógica de negócio está no CartService, as views apenas
consomem o serviço e renderizam respostas.
"""
import json
import logging

from django.contrib import messages
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse

from plataforma_de_servicos.cart.cart import Cart
from plataforma_de_servicos.cart.services import CartService

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
    """Exibe a página completa do carrinho."""
    service = CartService(request)
    context = {
        "cart": service.get_cart(),
    }
    return render(request, "pages/cart-summary.html", context)


def cart_add(request):
    """Adiciona item ao carrinho via CartService."""
    service = CartService(request)

    if request.POST.get("action") == "post":
        product_id = request.POST.get("product_id")
        variation_id = request.POST.get("variation_id")
        product_quantity = int(request.POST.get("product_quantity", 1))
        no_redirect = request.POST.get("no_redirect")

        # Usar o serviço para adicionar
        result = service.add_item(
            product_id=int(product_id) if product_id and not variation_id else None,
            variation_id=int(variation_id) if variation_id else None,
            quantity=product_quantity,
        )

        if not result.success:
            messages.error(request, result.message)
            if request.headers.get("HX-Request"):
                if no_redirect:
                    response = HttpResponse(_render_cart_badge(request, service.get_cart()))
                    response["HX-Trigger"] = json.dumps({
                        "showToast": {"message": result.message, "type": "error"},
                    })
                    return response
                return JsonResponse({
                    "error": True,
                    "message": result.message,
                    "redirect": reverse("cart:cart-summary"),
                })
            return redirect("cart:cart-summary")

        messages.success(request, result.message)
        if request.headers.get("HX-Request"):
            if no_redirect:
                response = HttpResponse(_render_cart_badge(request, service.get_cart()))
                response["HX-Trigger"] = json.dumps({
                    "showToast": {"message": result.message, "type": "success"},
                    "openCartOffcanvas": True,
                })
                return response
            return JsonResponse({
                "success": True,
                "message": result.message,
                "redirect": reverse("cart:cart-summary"),
                "qty": result.cart_quantity,
            })

        return redirect("cart:cart-summary")

    return JsonResponse({"error": "Invalid request"}, status=400)


def cart_delete(request):
    """Remove item do carrinho via CartService."""
    service = CartService(request)

    if request.POST.get("action") == "post":
        variation_id = request.POST.get("variation_id")
        result = service.remove_item(item_key=variation_id)

        messages.success(request, result.message)
        return JsonResponse({
            "qty": result.cart_quantity,
            "total": f"{result.cart_total:.2f}",
        })

    return JsonResponse({"error": "Invalid request"}, status=400)


def cart_delete_mini(request):
    """Remove item do carrinho e retorna o offcanvas atualizado."""
    service = CartService(request)

    if request.POST.get("action") == "post":
        variation_id = request.POST.get("variation_id")
        result = service.remove_item(item_key=variation_id)

        response = HttpResponse(_render_cart_offcanvas(request, service.get_cart()))
        response["HX-Trigger"] = json.dumps({
            "showToast": {
                "message": result.message,
                "type": "success" if result.success else "error",
            },
        })
        return response

    return JsonResponse({"error": "Invalid request"}, status=400)


def cart_update(request):
    """Atualiza quantidade de item no carrinho via CartService."""
    service = CartService(request)

    if request.POST.get("action") == "post":
        variation_id = request.POST.get("variation_id")
        product_quantity = int(request.POST.get("product_quantity"))

        result = service.update_item(
            item_key=variation_id,
            quantity=product_quantity,
        )

        if not result.success:
            return JsonResponse({
                "error": result.message,
            }, status=400)

        messages.success(request, result.message)
        return JsonResponse({
            "qty": result.cart_quantity,
            "total": f"{result.cart_total:.2f}",
            "item_total": f"{result.item_total:.2f}" if result.item_total else "0.00",
        })

    return JsonResponse({"error": "Invalid request"}, status=400)


def cart_increment(request):
    """Incrementa quantidade de item no carrinho (+1)."""
    service = CartService(request)

    if request.POST.get("action") == "post":
        item_key = request.POST.get("item_key")
        result = service.increment_item(item_key=item_key)

        if not result.success:
            response = HttpResponse(_render_cart_offcanvas(request, service.get_cart()))
            response["HX-Trigger"] = json.dumps({
                "showToast": {"message": result.message, "type": "error"},
            })
            return response

        response = HttpResponse(_render_cart_offcanvas(request, service.get_cart()))
        response["HX-Trigger"] = json.dumps({
            "cartUpdated": {
                "qty": result.cart_quantity,
                "total": f"{result.cart_total:.2f}",
            },
        })
        return response

    return JsonResponse({"error": "Invalid request"}, status=400)


def cart_decrement(request):
    """Decrementa quantidade de item no carrinho (-1)."""
    service = CartService(request)

    if request.POST.get("action") == "post":
        item_key = request.POST.get("item_key")
        result = service.decrement_item(item_key=item_key)

        response = HttpResponse(_render_cart_offcanvas(request, service.get_cart()))
        if result.success:
            response["HX-Trigger"] = json.dumps({
                "cartUpdated": {
                    "qty": result.cart_quantity,
                    "total": f"{result.cart_total:.2f}",
                },
            })
        else:
            response["HX-Trigger"] = json.dumps({
                "showToast": {"message": result.message, "type": "error"},
            })
        return response

    return JsonResponse({"error": "Invalid request"}, status=400)
