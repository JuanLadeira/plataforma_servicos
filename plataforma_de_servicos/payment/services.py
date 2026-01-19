import logging
from django.db import transaction

from .models import Order, OrderItem
from plataforma_de_servicos.cart.models import ReservaEstoque
from plataforma_de_servicos.estoque.services import EstoqueService

logger = logging.getLogger("django")


class PaymentService:
    """Service para operações de pagamento e finalização de pedidos"""
    
    @staticmethod
    @transaction.atomic
    def complete_order(cart, user_data, user=None):
        """
        Finaliza um pedido criando Order, OrderItems, saída de estoque e limpando reservas
        
        Args:
            cart: Instância do carrinho
            user_data: Dict com dados do usuário (name, email, address1, etc.)
            user: Usuário logado ou None para guest
            
        Returns:
            Order: Pedido criado
        """
        # All-in-one shipping address
        shipping_address = f"{user_data['address1']}\n{user_data.get('address2', '')}\n{user_data['city']}\n{user_data['state']}\n{user_data['zipcode']}"
        
        total_cost = cart.get_total()
        
        # Criar o pedido
        order_data = {
            'full_name': user_data['name'],
            'email': user_data['email'],
            'shipping_address': shipping_address,
            'amount_paid': total_cost,
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
        
        # Criar saída de estoque via service
        try:
            EstoqueService.criar_saida_por_pedido(
                pedido_id=order.id,
                itens_pedido=itens_estoque,
                funcionario=user if user and user.is_authenticated else None
            )
            logger.info(f"Saída de estoque criada para pedido {order.id}")
        except Exception as e:
            logger.error(f"Erro ao criar saída de estoque para pedido {order.id}: {e}")
            # O pedido continua, mas registra o erro
        
        # Limpar reservas do carrinho
        PaymentService.clear_cart_reservations(cart.session_key)
        
        return order
    
    @staticmethod
    def clear_cart_reservations(session_key):
        """
        Limpa as reservas de estoque de uma sessão específica
        
        Args:
            session_key: Chave da sessão para limpar
        """
        if not session_key:
            logger.warning("Session key não fornecida para limpeza de reservas")
            return
            
        try:
            deleted_count = ReservaEstoque.objects.filter(session_key=session_key).delete()[0]
            if deleted_count > 0:
                logger.info(f"Limpas {deleted_count} reservas de estoque para sessão {session_key}")
            else:
                logger.debug(f"Nenhuma reserva encontrada para sessão {session_key}")
        except Exception as e:
            logger.error(f"Erro ao limpar reservas para sessão {session_key}: {e}")
    
    @staticmethod
    def clear_session_cart_data(request):
        """
        Limpa dados do carrinho da sessão
        
        Args:
            request: Request object do Django
        """
        session_key = (
            getattr(request.session, '_session_key', None) or
            request.session.session_key
        )
        
        # Limpar reservas de estoque se necessário (fallback)
        if session_key:
            PaymentService.clear_cart_reservations(session_key)
        
        # Limpar dados do carrinho da sessão
        for key in list(request.session.keys()):
            if key == 'session_key':
                del request.session[key]