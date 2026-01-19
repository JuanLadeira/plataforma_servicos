from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from plataforma_de_servicos.produto.models import Produto, VariacaoProduto
from .models import ReservaEstoque


class Cart:
    def __init__(self, request):
        self.session = request.session
        self.session_key = request.session.session_key
        if not self.session_key:
            request.session.create()
            self.session_key = request.session.session_key
            
        cart = self.session.get("cart")
        if "cart" not in request.session:
            cart = self.session["cart"] = {}
        self.cart = cart

    def _create_or_update_reserva(self, produto=None, variacao_produto=None, quantidade=0):
        """Criar ou atualizar reserva de estoque"""
        
        try:
            if variacao_produto:
                reserva, created = ReservaEstoque.objects.get_or_create(
                    session_key=self.session_key,
                    variacao_produto=variacao_produto,
                    defaults={'quantidade': quantidade}
                )
            else:
                reserva, created = ReservaEstoque.objects.get_or_create(
                    session_key=self.session_key,
                    produto=produto,
                    defaults={'quantidade': quantidade}
                )
            
            if not created:
                reserva.quantidade = quantidade
                reserva.expires_at = timezone.now() + timezone.timedelta(minutes=30)
                reserva.save()
                
        except Exception as e:
            # Log do erro se necessário
            pass

    def add(self, variation: VariacaoProduto, product_qty: int):
        with transaction.atomic():
            # Lock a linha da variação para evitar race conditions
            variation_locked = VariacaoProduto.objects.select_for_update().get(pk=variation.pk)
            variation_id = str(variation.id)
            quantidade_no_carrinho = self.cart.get(variation_id, {}).get("qty", 0)

            # Calcular a quantidade já reservada por outros usuários
            try:
                quantidade_reservada = (
                    ReservaEstoque.get_quantidade_reservada(variacao_produto=variation_locked)
                    - quantidade_no_carrinho
                )
            except Exception:
                quantidade_reservada = 0

            estoque_disponivel = variation_locked.estoque - quantidade_reservada
            quantidade_a_adicionar = product_qty

            if estoque_disponivel < quantidade_a_adicionar:
                raise ValueError("Estoque insuficiente.")

            nova_quantidade = quantidade_no_carrinho + quantidade_a_adicionar

            if variation_id in self.cart:
                self.cart[variation_id]["qty"] = nova_quantidade
            else:
                preco_final = variation.calcular_preco_final()
                self.cart[variation_id] = {
                    "preco": str(preco_final),
                    "qty": nova_quantidade,
                }

            self._create_or_update_reserva(variacao_produto=variation, quantidade=nova_quantidade)
            self.session.modified = True

    def add_product(self, produto: Produto, product_qty: int):
        """Adiciona produto simples (sem variação) ao carrinho"""
        with transaction.atomic():
            produto_locked = Produto.objects.select_for_update().get(pk=produto.pk)
            product_id = f"produto_{produto.id}"
            quantidade_no_carrinho = self.cart.get(product_id, {}).get("qty", 0)

            try:
                quantidade_reservada = (
                    ReservaEstoque.get_quantidade_reservada(produto=produto_locked)
                    - quantidade_no_carrinho
                )
            except Exception:
                quantidade_reservada = 0

            estoque_disponivel = produto_locked.estoque - quantidade_reservada
            quantidade_a_adicionar = product_qty

            if estoque_disponivel < quantidade_a_adicionar:
                raise ValueError("Estoque insuficiente.")

            nova_quantidade = quantidade_no_carrinho + quantidade_a_adicionar
            
            if product_id in self.cart:
                self.cart[product_id]["qty"] = nova_quantidade
            else:
                self.cart[product_id] = {
                    "preco": str(produto.preco),
                    "qty": nova_quantidade,
                    "produto_id": produto.id,
                }
            
            # Atualizar reserva de estoque
            self._create_or_update_reserva(produto=produto, quantidade=nova_quantidade)
            self.session.modified = True

    def _remove_reserva(self, produto_id=None, variation_id=None):
        """Remove reserva de estoque"""
        
        try:
            if variation_id:
                ReservaEstoque.objects.filter(
                    session_key=self.session_key,
                    variacao_produto_id=variation_id
                ).delete()
            elif produto_id:
                ReservaEstoque.objects.filter(
                    session_key=self.session_key,
                    produto_id=produto_id
                ).delete()
        except Exception as e:
            pass

    def delete(self, variation):
        variation_id = str(variation)
        if variation_id in self.cart:
            # Remover reserva de estoque
            if variation_id.startswith("produto_"):
                produto_id = variation_id.replace("produto_", "")
                self._remove_reserva(produto_id=produto_id)
            else:
                self._remove_reserva(variation_id=variation_id)
            
            del self.cart[variation_id]
        self.session.modified = True

    def update(self, variation, qty):
        variation_id = str(variation)
        if variation_id in self.cart:
            self.cart[variation_id]["qty"] = qty
            
            # Atualizar reserva de estoque
            if variation_id.startswith("produto_"):
                produto_id = int(variation_id.replace("produto_", ""))
                produto = Produto.objects.get(id=produto_id)
                self._create_or_update_reserva(produto=produto, quantidade=qty)
            else:
                variation_obj = VariacaoProduto.objects.get(id=variation_id)
                self._create_or_update_reserva(variacao_produto=variation_obj, quantidade=qty)
                
        self.session.modified = True

    def __len__(self):
        return sum(item["qty"] for item in self.cart.values())

    def __iter__(self):
        all_variation_ids = []
        produto_ids = []
        
        # Separar IDs de variações e produtos
        for key in self.cart.keys():
            if key.startswith('produto_'):
                produto_ids.append(int(key.replace('produto_', '')))
            else:
                all_variation_ids.append(key)
        
        # Eagerly load related product and attribute data
        variations = VariacaoProduto.objects.filter(id__in=all_variation_ids).select_related(
            "produto"
        ).prefetch_related("valores__atributo")
        
        produtos = Produto.objects.filter(id__in=produto_ids) if produto_ids else []

        cart = self.cart.copy()
        
        # Atualizar variações com preço recalculado
        for variation in variations:
            preco_atual = variation.calcular_preco_final()
            cart[str(variation.id)]["variation"] = variation
            cart[str(variation.id)]["preco"] = str(preco_atual)
        
        # Atualizar produtos simples
        for produto in produtos:
            produto_key = f"produto_{produto.id}"
            if produto_key in cart:
                cart[produto_key]["produto"] = produto

        for item in cart.values():
            item["preco"] = Decimal(item["preco"])
            item["total"] = item["preco"] * item["qty"]
            yield item

    def get_total(self):
        return sum(Decimal(item["preco"]) * item["qty"] for item in self.cart.values())
    
    def clear(self):
        """Limpa o carrinho e remove todas as reservas"""
        try:
            # Limpar reservas de estoque
            ReservaEstoque.objects.filter(session_key=self.session_key).delete()
        except Exception:
            pass
        
        # Limpar carrinho
        self.session["session_key"] = {}
        self.cart = {}
        self.session.modified = True