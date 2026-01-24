import logging

from celery import shared_task

from .services import enviar_notificacao_interesse

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def notificar_corretores_novo_interesse(self, interesse_id: int) -> dict:
    """
    Task Celery para enviar notificação de novo interesse aos corretores.

    Executa de forma assíncrona com retry automático em caso de falha.

    Args:
        interesse_id: ID do InteresseCompra

    Returns:
        dict com resultado do envio
    """
    logger.info(f"Iniciando notificação de interesse #{interesse_id}")

    resultado = enviar_notificacao_interesse(interesse_id)

    if not resultado.get("success"):
        logger.error(f"Falha na notificação: {resultado.get('error')}")

    return resultado
