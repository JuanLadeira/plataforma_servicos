from django.shortcuts import render
from django.http import JsonResponse
import logging

from .models import ShippingAddress
from .services import PaymentService
from plataforma_de_servicos.cart.cart import Cart

logger = logging.getLogger("django")


def checkout(request):

    # Users with accounts -- Pre-fill the form

    if request.user.is_authenticated:

        try:

            # Authenticated users WITH shipping information 

            shipping_address = ShippingAddress.objects.get(user=request.user.id)

            context = {'shipping': shipping_address}

            


            return render(request, 'payment/checkout.html', context=context)


        except:

            # Authenticated users with NO shipping information

            return render(request, 'payment/checkout.html')

    else:
            
        # Guest users

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









