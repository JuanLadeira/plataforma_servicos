"""
View para consulta de saldo de variação em inventário.
"""

import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from plataforma_de_servicos.produto.models import VariacaoProduto

logger = logging.getLogger(__name__)


@require_GET
@staff_member_required
def get_saldo_variacao(request):
    """
    Retorna o saldo de uma variação em um inventário específico.

    Parâmetros GET:
        - variacao_id: ID da variação
        - inventario_id: ID do inventário

    Retorna JSON:
        - saldo: quantidade atual no inventário
        - variacao: nome da variação
        - produto: nome do produto
    """
    variacao_id = request.GET.get("variacao_id")
    inventario_id = request.GET.get("inventario_id")

    logger.debug(f"Consultando saldo para variacao_id={variacao_id} e inventario_id={inventario_id}")
    print(f"Consultando saldo para variacao_id={variacao_id} e inventario_id={inventario_id}")

    if not variacao_id or not inventario_id:
        logger.warning("Parâmetros variacao_id ou inventario_id ausentes na requisição")
        return JsonResponse({
            "error": "variacao_id e inventario_id são obrigatórios",
            "saldo": 0,
        }, status=400)


    try:
        variacao = VariacaoProduto.objects.select_related("produto").prefetch_related("valores").get(pk=variacao_id)
        variacao_estoque = variacao.estoque

        logger.debug(f"Variação encontrada: {variacao} para variacao_id={variacao_id}")
    except VariacaoProduto.DoesNotExist:
        return JsonResponse({
            "error": "Variação não encontrada",
            "saldo": 0,
        }, status=404)

    # Monta nome da variação
    valores = ", ".join(v.valor for v in variacao.valores.all())
    variacao_nome = f"{variacao.produto.produto} - {valores}" if valores else variacao.produto.produto

    return JsonResponse({
        "saldo": variacao_estoque,
        "variacao": variacao_nome,
        "produto": variacao.produto.produto,
        "variacao_id": variacao.id,
        "inventario_id": int(inventario_id),
    })
