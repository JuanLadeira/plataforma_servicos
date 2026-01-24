import logging
from decimal import Decimal

from django.contrib import messages
from django.shortcuts import redirect
from django.shortcuts import render

from plataforma_de_servicos.cart.cart import Cart

from .forms import InteresseCompraForm
from .models import InteresseCompra
from .models import ItemInteresse
from .tasks import notificar_corretores_novo_interesse

logger = logging.getLogger(__name__)


def interesse_compra_view(request):
    """View para o formulário de demonstração de interesse."""
    cart = Cart(request)

    if len(cart) == 0:
        messages.warning(request, "Seu carrinho está vazio.")
        return redirect("cart:cart-summary")

    if request.method == "POST":
        form = InteresseCompraForm(request.POST)
        if form.is_valid():
            interesse = form.save(commit=False)
            interesse.valor_total = Decimal(str(cart.get_total()))
            interesse.save()

            # Criar itens do interesse baseado no carrinho
            for item in cart:
                if item.get("variation"):
                    variation = item["variation"]
                    produto = variation.produto
                    variacao_info = ", ".join(
                        f"{v.atributo.nome}: {v.valor}"
                        for v in variation.valores.all()
                    )
                    ItemInteresse.objects.create(
                        interesse=interesse,
                        produto_nome=produto.produto,
                        variacao_info=variacao_info,
                        quantidade=item["qty"],
                        preco_unitario=Decimal(str(item["preco"])),
                    )
                elif item.get("produto"):
                    produto = item["produto"]
                    ItemInteresse.objects.create(
                        interesse=interesse,
                        produto_nome=produto.produto,
                        variacao_info="",
                        quantidade=item["qty"],
                        preco_unitario=Decimal(str(item["preco"])),
                    )

            # Limpar o carrinho
            cart.clear()

            # Notificar corretores de forma assíncrona
            try:
                notificar_corretores_novo_interesse.delay(interesse.pk)
                logger.info(f"Task de notificação enfileirada para interesse #{interesse.pk}")
            except Exception as e:
                # Não bloquear o fluxo se houver erro no Celery
                logger.error(f"Erro ao enfileirar notificação: {e}")

            messages.success(
                request,
                "Seu interesse foi registrado com sucesso! "
                "Em breve um de nossos corretores entrará em contato.",
            )
            return redirect("corretor:interesse-sucesso", interesse_id=interesse.pk)
    else:
        form = InteresseCompraForm()

    context = {
        "form": form,
        "cart": cart,
    }
    return render(request, "corretor/interesse_compra.html", context)


def interesse_sucesso_view(request, interesse_id):
    """View de confirmação após registro do interesse."""
    try:
        interesse = InteresseCompra.objects.prefetch_related("itens").get(pk=interesse_id)
    except InteresseCompra.DoesNotExist:
        messages.error(request, "Interesse não encontrado.")
        return redirect("home")

    context = {
        "interesse": interesse,
    }
    return render(request, "corretor/interesse_sucesso.html", context)
