import logging

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.urls import reverse

from plataforma_de_servicos.cart.cart import Cart
from plataforma_de_servicos.cart.models import ReservaEstoque
from plataforma_de_servicos.produto.models import VariacaoProduto, Produto

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
        # Verificar se é produto simples ou variação
        product_id = request.POST.get("product_id")
        variation_id = request.POST.get("variation_id")
        product_quantity = int(request.POST.get("product_quantity", 1))

        if variation_id:
            # Produto com variações
            variation = get_object_or_404(VariacaoProduto, id=variation_id)
            produto = variation.produto
            estoque_atual = variation.estoque
            produto_nome = f"{produto.produto} ({variation})"
        else:
            # Produto simples
            produto = get_object_or_404(Produto, id=product_id)
            estoque_atual = produto.estoque
            produto_nome = produto.produto

        # Verificar quantidade já no carrinho
        cart_key = str(variation_id) if variation_id else f"produto_{product_id}"
        quantidade_no_carrinho = cart.cart.get(cart_key, {}).get("qty", 0)
        quantidade_total_solicitada = quantidade_no_carrinho + product_quantity

        # Verificar quantidade reservada por outros usuários
        if variation_id:
            # Buscar o objeto variação para passar ao método
            try:
                variacao_obj = variation_id  # Se for objeto
                if hasattr(variation_id, 'id'):  # Se for instância de VariacaoProduto
                    variacao_obj = variation_id
                else:  # Se for ID
                    variacao_obj = VariacaoProduto.objects.get(id=variation_id)
                
                quantidade_reservada_outros = ReservaEstoque.get_quantidade_reservada(variacao_produto=variacao_obj)
            except:
                quantidade_reservada_outros = 0
                
            # Subtrair nossa própria reserva se existir
            nossa_reserva = ReservaEstoque.objects.filter(
                session_key=cart.session_key,
                variacao_produto_id=variation_id
            ).first()
            if nossa_reserva:
                quantidade_reservada_outros -= nossa_reserva.quantidade
        else:
            # Passar o objeto produto ao método
            try:
                quantidade_reservada_outros = ReservaEstoque.get_quantidade_reservada(produto=produto)
            except:
                quantidade_reservada_outros = 0
            
            # Subtrair nossa própria reserva se existir
            nossa_reserva = ReservaEstoque.objects.filter(
                session_key=cart.session_key,
                produto_id=product_id
            ).first()
            if nossa_reserva:
                quantidade_reservada_outros -= nossa_reserva.quantidade

        # Estoque disponível = estoque atual - reservas de outros usuários
        estoque_disponivel = estoque_atual - quantidade_reservada_outros

        # Verificar se há estoque suficiente
        if quantidade_total_solicitada > estoque_disponivel:
            disponivel_para_adicionar = estoque_disponivel - quantidade_no_carrinho
            if disponivel_para_adicionar <= 0:
                messages.error(
                    request, 
                    f"Este produto já está no seu carrinho e não há mais estoque disponível!"
                )
            else:
                messages.error(
                    request, 
                    f"Estoque insuficiente! Você já tem {quantidade_no_carrinho} unidades no carrinho. "
                    f"Disponível para adicionar: {disponivel_para_adicionar} unidades."
                )
            
            # Retornar resposta apropriada baseada no tipo de requisição
            if request.headers.get("HX-Request"):
                return JsonResponse({
                    "error": "Estoque insuficiente",
                    "redirect": reverse("cart:cart-summary")
                })
            else:
                return redirect("cart:cart-summary")

        # Adicionar ao carrinho
        if variation_id:
            cart.add(variation=variation, product_qty=product_quantity)
        else:
            # Para produtos simples, criar método no cart.py
            cart.add_product(produto=produto, product_qty=product_quantity)

        cart_quantity = len(cart)
        messages.success(request, f"{produto_nome} adicionado ao carrinho com sucesso!")
        
        # Redirecionamento baseado no tipo de requisição
        if request.headers.get("HX-Request"):
            return JsonResponse({
                "qty": cart_quantity,
                "redirect": reverse("cart:cart-summary")
            })
        else:
            return redirect("cart:cart-summary")
    
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