import logging
from django.db import transaction

from .models import Order, OrderItem
from plataforma_de_servicos.estoque.services import EstoqueService

logger = logging.getLogger("django")


class PaymentService:
    """Service para operações de pagamento e finalização de pedidos"""

    @staticmethod
    @transaction.atomic
    def complete_order(cart, user_data, user=None, empresa=None):
        """
        Finaliza um pedido criando Order, OrderItems, saída de estoque e limpando reservas

        Args:
            cart: Instância do carrinho
            user_data: Dict com dados do usuário (name, email, address1, etc.)
            user: Usuário logado ou None para guest
            empresa: Empresa (tenant) associada ao pedido

        Returns:
            Order: Pedido criado
        """
        # All-in-one shipping address
        shipping_address = f"{user_data['address1']}\n{user_data.get('address2', '')}\n{user_data['city']}\n{user_data['state']}\n{user_data['zipcode']}"

        total_cost = cart.get_total()

        # Criar o pedido com empresa associada
        order_data = {
            'full_name': user_data['name'],
            'email': user_data['email'],
            'shipping_address': shipping_address,
            'amount_paid': total_cost,
            'empresa': empresa,
        }

        if user and user.is_authenticated:
            order_data['user'] = user

        order = Order.objects.create(**order_data)
        
        # Criar itens do pedido e preparar para saída de estoque
        itens_estoque = []
        
        for item in cart:
            if 'variation' in item:
                # Item com variação
                OrderItem.objects.create(
                    order=order,
                    variacao_produto=item['variation'],
                    produto=item['variation'].produto,
                    quantity=item['qty'],
                    price=item['preco'],
                    user=user if user and user.is_authenticated else None
                )
                itens_estoque.append({
                    'produto': item['variation'].produto,
                    'quantidade': item['qty'],
                    'variacao': item['variation']
                })
            else:
                # Item simples
                OrderItem.objects.create(
                    order=order,
                    produto=item['produto'],
                    quantity=item['qty'],
                    price=item['preco'],
                    user=user if user and user.is_authenticated else None
                )
                itens_estoque.append({
                    'produto': item['produto'],
                    'quantidade': item['qty'],
                    'variacao': None
                })
        
        # Criar saída de estoque manual (sem ordem de compra associada)
        try:
            from plataforma_de_servicos.estoque.choices.origem_saida import OrigemSaida
            saida = EstoqueService.criar_saida_manual(
                origem=OrigemSaida.PEDIDO.value,
                itens=itens_estoque,
                funcionario=user if user and user.is_authenticated else None,
                observacao=f"Saída automática para pagamento - Order #{order.id}",
            )
            saida.processar()
            logger.info(f"Saída de estoque criada para pedido {order.id}")
        except Exception as e:
            logger.error(f"Erro ao criar saída de estoque para pedido {order.id}: {e}")
            # O pedido continua, mas registra o erro
        
        return order
    
    @staticmethod
    def clear_session_cart_data(request):
        """
        Limpa dados do carrinho da sessão
        
        Args:
            request: Request object do Django
        """
        # Limpar dados do carrinho da sessão
        if 'cart' in request.session:
            del request.session['cart']