"""
CartService - Camada de serviço para manipulação do carrinho de compras.

Segue o padrão Model -> Service -> View, encapsulando toda a lógica de negócio
relacionada ao carrinho, validações de estoque e cálculos.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from django.shortcuts import get_object_or_404

from plataforma_de_servicos.cart.cart import Cart
from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.produto.models import VariacaoProduto

if TYPE_CHECKING:
    from django.http import HttpRequest


@dataclass
class CartOperationResult:
    """Resultado de uma operação no carrinho."""
    success: bool
    message: str
    cart_quantity: int = 0
    cart_total: Decimal = Decimal("0.00")
    item_total: Decimal | None = None
    error_type: str | None = None


@dataclass
class CartItemInfo:
    """Informações sobre um item do carrinho."""
    item_key: str
    product_name: str
    unit_price: Decimal
    quantity: int
    max_stock: int
    is_variation: bool
    variation_id: int | None = None
    product_id: int | None = None


class CartService:
    """
    Serviço para gerenciamento do carrinho de compras.

    Encapsula toda a lógica de negócio para adicionar, remover, atualizar
    e consultar itens no carrinho, com validação de estoque e tenant.
    """

    def __init__(self, request: "HttpRequest"):
        self.request = request
        self.cart = Cart(request)
        self.tenant = getattr(request, "tenant", None)

    def add_item(
        self,
        product_id: int | None = None,
        variation_id: int | None = None,
        quantity: int = 1,
    ) -> CartOperationResult:
        """
        Adiciona um item ao carrinho com validação de estoque.

        Args:
            product_id: ID do produto simples (sem variação)
            variation_id: ID da variação do produto
            quantity: Quantidade a adicionar

        Returns:
            CartOperationResult com status da operação
        """
        if quantity <= 0:
            return CartOperationResult(
                success=False,
                message="Quantidade deve ser maior que zero.",
                cart_quantity=len(self.cart),
                cart_total=self.cart.get_total(),
                error_type="invalid_quantity",
            )

        item_info = self._get_item_info(product_id, variation_id)
        if item_info is None:
            return CartOperationResult(
                success=False,
                message="Produto não encontrado.",
                cart_quantity=len(self.cart),
                cart_total=self.cart.get_total(),
                error_type="not_found",
            )

        # Validar estoque
        current_qty_in_cart = self.cart.cart.get(item_info.item_key, {}).get("qty", 0)
        total_requested = current_qty_in_cart + quantity

        if total_requested > item_info.max_stock:
            if current_qty_in_cart > 0:
                error_msg = (
                    f"Você já adicionou a quantidade máxima de "
                    f"'{item_info.product_name}' ao seu carrinho."
                )
            else:
                error_msg = (
                    f"Estoque insuficiente para '{item_info.product_name}'. "
                    f"Disponível: {item_info.max_stock}."
                )
            return CartOperationResult(
                success=False,
                message=error_msg,
                cart_quantity=len(self.cart),
                cart_total=self.cart.get_total(),
                error_type="insufficient_stock",
            )

        # Adicionar ao carrinho
        if item_info.is_variation:
            variation = self._get_variation(variation_id)
            self.cart.add(variation=variation, product_qty=quantity)
        else:
            produto = self._get_product(product_id)
            self.cart.add_product(produto=produto, product_qty=quantity)

        return CartOperationResult(
            success=True,
            message=f"{item_info.product_name} adicionado ao carrinho!",
            cart_quantity=len(self.cart),
            cart_total=self.cart.get_total(),
            item_total=item_info.unit_price * quantity,
        )

    def update_item(
        self,
        item_key: str,
        quantity: int,
    ) -> CartOperationResult:
        """
        Atualiza a quantidade de um item no carrinho.

        Args:
            item_key: Chave do item (variation_id ou "produto_{id}")
            quantity: Nova quantidade

        Returns:
            CartOperationResult com status da operação
        """
        if quantity < 1:
            return CartOperationResult(
                success=False,
                message="Quantidade mínima: 1",
                cart_quantity=len(self.cart),
                cart_total=self.cart.get_total(),
                error_type="invalid_quantity",
            )

        # Determinar tipo de item
        if item_key.startswith("produto_"):
            product_id = int(item_key.replace("produto_", ""))
            item_info = self._get_item_info(product_id=product_id)
        else:
            item_info = self._get_item_info(variation_id=int(item_key))

        if item_info is None:
            return CartOperationResult(
                success=False,
                message="Produto não encontrado.",
                cart_quantity=len(self.cart),
                cart_total=self.cart.get_total(),
                error_type="not_found",
            )

        # Validar estoque
        if quantity > item_info.max_stock:
            return CartOperationResult(
                success=False,
                message=f"Quantidade máxima disponível: {item_info.max_stock}",
                cart_quantity=len(self.cart),
                cart_total=self.cart.get_total(),
                error_type="insufficient_stock",
            )

        # Atualizar
        self.cart.update(variation=item_key, qty=quantity)

        return CartOperationResult(
            success=True,
            message="Carrinho atualizado com sucesso!",
            cart_quantity=len(self.cart),
            cart_total=self.cart.get_total(),
            item_total=item_info.unit_price * quantity,
        )

    def remove_item(self, item_key: str) -> CartOperationResult:
        """
        Remove um item do carrinho.

        Args:
            item_key: Chave do item (variation_id ou "produto_{id}")

        Returns:
            CartOperationResult com status da operação
        """
        if item_key not in self.cart.cart:
            return CartOperationResult(
                success=False,
                message="Item não encontrado no carrinho.",
                cart_quantity=len(self.cart),
                cart_total=self.cart.get_total(),
                error_type="not_found",
            )

        self.cart.delete(variation=item_key)

        return CartOperationResult(
            success=True,
            message="Item removido do carrinho!",
            cart_quantity=len(self.cart),
            cart_total=self.cart.get_total(),
        )

    def increment_item(self, item_key: str, amount: int = 1) -> CartOperationResult:
        """
        Incrementa a quantidade de um item no carrinho.

        Args:
            item_key: Chave do item
            amount: Quantidade a incrementar (padrão: 1)

        Returns:
            CartOperationResult com status da operação
        """
        current_qty = self.cart.cart.get(item_key, {}).get("qty", 0)
        if current_qty == 0:
            return CartOperationResult(
                success=False,
                message="Item não encontrado no carrinho.",
                cart_quantity=len(self.cart),
                cart_total=self.cart.get_total(),
                error_type="not_found",
            )

        return self.update_item(item_key, current_qty + amount)

    def decrement_item(self, item_key: str, amount: int = 1) -> CartOperationResult:
        """
        Decrementa a quantidade de um item no carrinho.

        Args:
            item_key: Chave do item
            amount: Quantidade a decrementar (padrão: 1)

        Returns:
            CartOperationResult com status da operação
        """
        current_qty = self.cart.cart.get(item_key, {}).get("qty", 0)
        if current_qty == 0:
            return CartOperationResult(
                success=False,
                message="Item não encontrado no carrinho.",
                cart_quantity=len(self.cart),
                cart_total=self.cart.get_total(),
                error_type="not_found",
            )

        new_qty = current_qty - amount
        if new_qty <= 0:
            return self.remove_item(item_key)

        return self.update_item(item_key, new_qty)

    def clear(self) -> CartOperationResult:
        """Limpa todos os itens do carrinho."""
        self.cart.clear()
        return CartOperationResult(
            success=True,
            message="Carrinho limpo com sucesso!",
            cart_quantity=0,
            cart_total=Decimal("0.00"),
        )

    def get_cart(self) -> Cart:
        """Retorna o objeto Cart para iteração."""
        return self.cart

    def get_total(self) -> Decimal:
        """Retorna o total do carrinho."""
        return self.cart.get_total()

    def get_item_count(self) -> int:
        """Retorna a quantidade total de itens no carrinho."""
        return len(self.cart)

    def _get_item_info(
        self,
        product_id: int | None = None,
        variation_id: int | None = None,
    ) -> CartItemInfo | None:
        """
        Obtém informações de um item (produto ou variação).

        Returns:
            CartItemInfo ou None se não encontrado
        """
        try:
            if variation_id:
                variation = self._get_variation(variation_id)
                return CartItemInfo(
                    item_key=str(variation_id),
                    product_name=f"{variation.produto.produto} ({variation})",
                    unit_price=variation.calcular_preco_final(),
                    quantity=0,
                    max_stock=variation.estoque,
                    is_variation=True,
                    variation_id=variation_id,
                )
            elif product_id:
                produto = self._get_product(product_id)
                return CartItemInfo(
                    item_key=f"produto_{product_id}",
                    product_name=produto.produto,
                    unit_price=produto.preco,
                    quantity=0,
                    max_stock=produto.estoque,
                    is_variation=False,
                    product_id=product_id,
                )
        except Exception:
            return None
        return None

    def _get_variation(self, variation_id: int) -> VariacaoProduto:
        """Obtém uma variação filtrada por tenant."""
        queryset = VariacaoProduto.objects.all()
        if self.tenant:
            queryset = queryset.filter(produto__empresa=self.tenant)
        return get_object_or_404(queryset, id=variation_id)

    def _get_product(self, product_id: int) -> Produto:
        """Obtém um produto filtrado por tenant."""
        queryset = Produto.objects.all()
        if self.tenant:
            queryset = queryset.filter(empresa=self.tenant)
        return get_object_or_404(queryset, id=product_id)
