from copy import deepcopy
from decimal import Decimal

from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.produto.models import VariacaoProduto


class Cart:
    """
    Uma classe de carrinho de compras otimista e baseada em sessão.
    O estoque é verificado apenas no momento do checkout.
    """
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get("cart")
        if "cart" not in request.session or not isinstance(cart, dict):
            cart = self.session["cart"] = {}
        self.cart = cart

    def add(self, variation: VariacaoProduto, product_qty: int):
        """Adiciona uma variação de produto ao carrinho ou atualiza sua quantidade."""
        variation_id = str(variation.id)

        if product_qty <= 0:
            # Não permite adicionar quantidade zero ou negativa
            return

        if variation_id in self.cart:
            self.cart[variation_id]["qty"] += product_qty
        else:
            preco_final = variation.calcular_preco_final()
            self.cart[variation_id] = {
                "preco": str(preco_final),
                "qty": product_qty,
            }
        self._save()

    def add_product(self, produto: Produto, product_qty: int):
        """Adiciona um produto simples (sem variação) ao carrinho."""
        product_id = f"produto_{produto.id}"

        if product_qty <= 0:
            return

        if product_id in self.cart:
            self.cart[product_id]["qty"] += product_qty
        else:
            self.cart[product_id] = {
                "preco": str(produto.preco),
                "qty": product_qty,
                "produto_id": produto.id,
            }
        self._save()

    def delete(self, variation):
        """Deleta um item (produto ou variação) do carrinho."""
        variation_id = str(variation)
        if variation_id in self.cart:
            del self.cart[variation_id]
            self._save()

    def update(self, variation, qty: int):
        """Atualiza a quantidade de um item no carrinho."""
        variation_id = str(variation)
        if variation_id in self.cart:
            if qty > 0:
                self.cart[variation_id]["qty"] = qty
                self._save()
            else:
                # Remove o item se a quantidade for zero ou menos
                self.delete(variation_id)

    def __len__(self):
        """Retorna a quantidade total de itens no carrinho."""
        return sum(item["qty"] for item in self.cart.values())

    def __iter__(self):
        """
        Itera sobre os itens do carrinho, buscando os objetos do banco de dados
        e preparando os dados para exibição.
        """
        all_variation_ids = [key for key in self.cart.keys() if not key.startswith("produto_")]
        produto_ids = [int(key.replace("produto_", "")) for key in self.cart.keys() if key.startswith("produto_")]

        variations = VariacaoProduto.objects.filter(id__in=all_variation_ids).select_related(
            "produto",
        ).prefetch_related("valores__atributo")

        produtos = Produto.objects.filter(id__in=produto_ids)

        cart = deepcopy(self.cart)

        for variation in variations:
            variation_key = str(variation.id)
            cart[variation_key]["variation"] = variation
            # Opcional: Recalcular preço para garantir que está atualizado
            cart[variation_key]["preco"] = str(variation.calcular_preco_final())

        for produto in produtos:
            produto_key = f"produto_{produto.id}"
            cart[produto_key]["produto"] = produto

        for item in cart.values():
            item["preco"] = Decimal(item["preco"])
            item["total"] = item["preco"] * item["qty"]
            yield item

    def get_total(self):
        """Calcula o valor total do carrinho."""
        return sum(Decimal(item["preco"]) * item["qty"] for item in self.cart.values())

    def clear(self):
        """Limpa o carrinho da sessão."""
        self.session["cart"] = {}
        self.cart = {}
        self._save()

    def _save(self):
        """Salva o carrinho na sessão."""
        self.session["cart"] = self.cart
        self.session.modified = True
