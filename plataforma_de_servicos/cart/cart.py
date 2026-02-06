from copy import deepcopy
from decimal import Decimal

from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.produto.models import VariacaoProduto


class Cart:
    """
    Uma classe de carrinho de compras otimista e baseada em sessão.
    O estoque é verificado apenas no momento do checkout.

    O carrinho é isolado por tenant (empresa) usando chave única na sessão.
    """
    def __init__(self, request):
        self.session = request.session
        self.tenant = getattr(request, "tenant", None)

        # Cart key per tenant for data isolation
        self.cart_key = f"cart_{self.tenant.slug}" if self.tenant else "cart"

        cart = self.session.get(self.cart_key)
        if self.cart_key not in request.session or not isinstance(cart, dict):
            cart = self.session[self.cart_key] = {}
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
        Filtra por tenant para evitar vazamento de dados entre empresas.
        """
        all_variation_ids = [key for key in self.cart.keys() if not key.startswith("produto_")]
        produto_ids = [int(key.replace("produto_", "")) for key in self.cart.keys() if key.startswith("produto_")]

        # Filtra variações por tenant
        variations_qs = VariacaoProduto.objects.filter(id__in=all_variation_ids).select_related(
            "produto",
        ).prefetch_related("valores__atributo")
        if self.tenant:
            variations_qs = variations_qs.filter(produto__empresa=self.tenant)
        variations = variations_qs

        # Filtra produtos por tenant
        produtos_qs = Produto.objects.filter(id__in=produto_ids)
        if self.tenant:
            produtos_qs = produtos_qs.filter(empresa=self.tenant)
        produtos = produtos_qs

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
        self.session[self.cart_key] = {}
        self.cart = {}
        self._save()

    def _save(self):
        """Salva o carrinho na sessão."""
        self.session[self.cart_key] = self.cart
        self.session.modified = True
