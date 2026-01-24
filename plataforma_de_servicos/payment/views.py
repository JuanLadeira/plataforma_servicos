from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
import logging

from .models import ShippingAddress
from .services import PaymentService
from plataforma_de_servicos.cart.cart import Cart

logger = logging.getLogger("django")


def checkout(request):
    cart = Cart(request)

    # Verificar estoque antes de prosseguir para o checkout
    for item in cart:
        produto_real = item.get('variation') or item.get('produto')
        if not produto_real:
            messages.error(request, "Um item no seu carrinho não foi encontrado e foi removido.")
            cart.delete(item.get('variation_id') or item.get('produto_id'))
            return redirect('cart:cart-summary')

        estoque_disponivel = produto_real.estoque
        if item['qty'] > estoque_disponivel:
            messages.error(
                request,
                f"Estoque insuficiente para '{produto_real}'. "
                f"Disponível: {estoque_disponivel}, no seu carrinho: {item['qty']}. "
                "Ajuste a quantidade para continuar."
            )
            return redirect('cart:cart-summary')

    # Se todos os itens têm estoque, continuar para o checkout
    if request.user.is_authenticated:
        try:
            shipping_address = ShippingAddress.objects.get(user=request.user)
            context = {'shipping': shipping_address}
            return render(request, 'payment/checkout.html', context=context)
        except ShippingAddress.DoesNotExist:
            return render(request, 'payment/checkout.html')
    else:
        return render(request, 'payment/checkout.html')



def complete_order(request):
    if request.POST.get('action') == 'post':
        try:
            user_data = {
                'name': request.POST.get('name'),
                'email': request.POST.get('email'),
                'address1': request.POST.get('address1'),
                'address2': request.POST.get('address2'),
                'city': request.POST.get('city'),
                'state': request.POST.get('state'),
                'zipcode': request.POST.get('zipcode')
            }

            cart = Cart(request)
            user = request.user if request.user.is_authenticated else None
            
            order = PaymentService.complete_order(cart, user_data, user)
            
            return JsonResponse({'success': True, 'order_id': order.id})
                
        except Exception as e:
            logger.error(f"Erro ao processar pedido: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=400)






    




def payment_success(request):
    # Limpar dados do carrinho e reservas (fallback)
    PaymentService.clear_session_cart_data(request)
    
    return render(request, 'payment/payment-success.html')







def payment_failed(request):

    return render(request, 'payment/payment-failed.html')









