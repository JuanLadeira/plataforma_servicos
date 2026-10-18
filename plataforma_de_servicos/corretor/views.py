import logging
from decimal import Decimal

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.shortcuts import render

from plataforma_de_servicos.cart.cart import Cart

from .forms import InteresseCompraForm
from .models import InteresseCompra
from .models import ItemInteresse
from .tasks import notificar_corretores_novo_interesse

logger = logging.getLogger(__name__)

# Chave de sessão com os ids dos interesses criados pelo visitante
SESSION_INTERESSES_KEY = "interesses_criados"


def interesse_compra_view(request):
    """View para o formulário de demonstração de interesse."""
    cart = Cart(request)

    if len(cart) == 0:
        messages.warning(request, "Seu carrinho está vazio.")
        return redirect("cart:cart-summary")

    # Sem tenant o interesse ficaria sem empresa (órfão)
    if not getattr(request, "tenant", None):
        raise Http404("Página não encontrada")

    if request.method == "POST":
        form = InteresseCompraForm(request.POST)
        if form.is_valid():
            interesse = form.save(commit=False)
            interesse.empresa = request.tenant
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

            # Só quem criou o interesse pode ver a página de confirmação
            criados = request.session.get(SESSION_INTERESSES_KEY, [])
            request.session[SESSION_INTERESSES_KEY] = [*criados[-9:], interesse.pk]

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
    tenant = getattr(request, "tenant", None)
    criados = request.session.get(SESSION_INTERESSES_KEY, [])

    interesse = None
    if tenant and interesse_id in criados:
        interesse = (
            InteresseCompra.objects.prefetch_related("itens")
            .filter(pk=interesse_id, empresa=tenant)
            .first()
        )

    if interesse is None:
        messages.error(request, "Interesse não encontrado.")
        return redirect("home")

    context = {
        "interesse": interesse,
    }
    return render(request, "corretor/interesse_sucesso.html", context)
