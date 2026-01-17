
from decimal import Decimal

from plataforma_de_servicos.produto.models import Produto, VariacaoProduto


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get("session_key")
        if "session_key" not in request.session:
            cart = self.session["session_key"] = {}
        self.cart = cart

    def add(self, variation: VariacaoProduto, product_qty: int):
        variation_id = str(variation.id)
        if variation_id in self.cart:
            self.cart[variation_id]["qty"] = product_qty
        else:
            self.cart[variation_id] = {
                "preco": str(variation.preco),
                "qty": product_qty,
            }
        self.session.modified = True

    def delete(self, variation):
        variation_id = str(variation)
        if variation_id in self.cart:
            del self.cart[variation_id]
        self.session.modified = True

    def update(self, variation, qty):
        variation_id = str(variation)
        if variation_id in self.cart:
            self.cart[variation_id]["qty"] = qty
        self.session.modified = True

    def __len__(self):
        return sum(item["qty"] for item in self.cart.values())

    def __iter__(self):
        all_variation_ids = self.cart.keys()
        # Eagerly load related product and attribute data
        variations = VariacaoProduto.objects.filter(id__in=all_variation_ids).select_related(
            "produto"
        ).prefetch_related("valores__atributo")

        cart = self.cart.copy()
        for variation in variations:
            cart[str(variation.id)]["variation"] = variation

        for item in cart.values():
            item["preco"] = Decimal(item["preco"])
            item["total"] = item["preco"] * item["qty"]
            yield item

    def get_total(self):
        return sum(Decimal(item["preco"]) * item["qty"] for item in self.cart.values())
