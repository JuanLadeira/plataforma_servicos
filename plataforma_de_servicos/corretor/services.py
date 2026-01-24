import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import Corretor
from .models import InteresseCompra

logger = logging.getLogger(__name__)


def get_corretores_ativos_emails():
    """Retorna lista de e-mails dos corretores ativos."""
    return list(
        Corretor.objects.filter(ativo=True).values_list("email", flat=True)
    )


def enviar_notificacao_interesse(interesse_id: int) -> dict:
    """
    Envia e-mail de notificação para todos os corretores ativos
    sobre um novo interesse de compra.

    Args:
        interesse_id: ID do InteresseCompra

    Returns:
        dict com status do envio
    """
    try:
        interesse = InteresseCompra.objects.prefetch_related("itens").get(pk=interesse_id)
    except InteresseCompra.DoesNotExist:
        logger.error(f"Interesse #{interesse_id} não encontrado para notificação")
        return {"success": False, "error": "Interesse não encontrado"}

    emails_corretores = get_corretores_ativos_emails()

    if not emails_corretores:
        logger.warning("Nenhum corretor ativo para notificar")
        return {"success": True, "enviados": 0, "motivo": "Nenhum corretor ativo"}

    # Preparar contexto para o template
    context = {
        "interesse": interesse,
        "itens": interesse.itens.all(),
        "site_url": getattr(settings, "SITE_URL", "http://localhost:8000"),
    }

    # Renderizar templates
    subject = f"Novo Interesse de Compra #{interesse.pk} - {interesse.nome_cliente}"
    html_message = render_to_string("corretor/emails/novo_interesse.html", context)
    plain_message = render_to_string("corretor/emails/novo_interesse.txt", context)

    try:
        enviados = send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=emails_corretores,
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(
            f"Notificação de interesse #{interesse_id} enviada para {enviados} corretor(es)"
        )

        return {
            "success": True,
            "enviados": enviados,
            "destinatarios": emails_corretores,
        }

    except Exception as e:
        logger.error(f"Erro ao enviar notificação de interesse #{interesse_id}: {e}")
        return {"success": False, "error": str(e)}
