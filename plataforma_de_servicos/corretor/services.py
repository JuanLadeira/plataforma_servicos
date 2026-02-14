import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from plataforma_de_servicos.empresa.models import Empresa
from plataforma_de_servicos.users.models import Funcionario

from .models import InteresseCompra
from .models import StatusInteresse

logger = logging.getLogger(__name__)


class InteresseCompraServiceError(Exception):
    """Exceção base para erros do serviço de InteresseCompra."""


class InteresseCompraService:
    """Serviço para gerenciar transições de status de InteresseCompra."""

    @staticmethod
    def gerar_numero(empresa: Empresa) -> str:
        """
        Gera número único por empresa no formato IC-YYYY-NNNNN.

        Args:
            empresa: Empresa para qual gerar o número

        Returns:
            str: Número do interesse (ex: IC-2026-00001)
        """
        ano = timezone.now().year
        prefixo = f"IC-{ano}-"

        ultimo_interesse = (
            InteresseCompra.objects.filter(
                empresa=empresa,
                numero__startswith=prefixo,
            )
            .order_by("-numero")
            .first()
        )

        if ultimo_interesse and ultimo_interesse.numero:
            try:
                ultimo_numero = int(ultimo_interesse.numero.split("-")[-1])
                novo_numero = ultimo_numero + 1
            except (ValueError, IndexError):
                novo_numero = 1
        else:
            novo_numero = 1

        return f"{prefixo}{novo_numero:05d}"

    @staticmethod
    @transaction.atomic
    def atender(interesse: InteresseCompra, funcionario: Funcionario) -> InteresseCompra:
        """
        Inicia o atendimento de um interesse.

        Args:
            interesse: InteresseCompra a ser atendido
            funcionario: Funcionario (corretor) que está assumindo o atendimento

        Returns:
            InteresseCompra atualizado

        Raises:
            InteresseCompraServiceError: Se o interesse não puder ser atendido
        """
        if not interesse.pode_atender:
            raise InteresseCompraServiceError(
                f"Interesse #{interesse.pk} não pode ser atendido. Status atual: {interesse.get_status_display()}",
            )

        interesse.status = StatusInteresse.EM_ATENDIMENTO
        interesse.corretor = funcionario
        interesse.save()

        return interesse

    @staticmethod
    @transaction.atomic
    def converter(interesse: InteresseCompra) -> InteresseCompra:
        """
        Converte o interesse para status CONVERTIDO.
        Isso dispara o signal que cria a OrdemCompra automaticamente.

        Args:
            interesse: InteresseCompra a ser convertido

        Returns:
            InteresseCompra atualizado

        Raises:
            InteresseCompraServiceError: Se o interesse não puder ser convertido
        """
        if not interesse.pode_converter:
            raise InteresseCompraServiceError(
                f"Interesse #{interesse.pk} não pode ser convertido. Status atual: {interesse.get_status_display()}",
            )

        if not interesse.corretor:
            raise InteresseCompraServiceError(
                "É necessário ter um corretor atribuído para converter o interesse.",
            )

        interesse.status = StatusInteresse.CONVERTIDO
        interesse.save()

        return interesse

    @staticmethod
    @transaction.atomic
    def descartar(interesse: InteresseCompra, motivo: str = "") -> InteresseCompra:
        """
        Descarta o interesse.

        Args:
            interesse: InteresseCompra a ser descartado
            motivo: Motivo do descarte (opcional, mas recomendado)

        Returns:
            InteresseCompra atualizado

        Raises:
            InteresseCompraServiceError: Se o interesse não puder ser descartado
        """
        if not interesse.pode_descartar:
            raise InteresseCompraServiceError(
                f"Interesse #{interesse.pk} não pode ser descartado. Status atual: {interesse.get_status_display()}",
            )

        interesse.status = StatusInteresse.DESCARTADO
        if motivo:
            interesse.mensagem = f"{interesse.mensagem}\n\n--- Motivo do descarte ---\n{motivo}".strip()
        interesse.save()

        return interesse

    @staticmethod
    @transaction.atomic
    def retornar(interesse: InteresseCompra) -> InteresseCompra:
        """
        Retorna o interesse para status NOVO.

        Args:
            interesse: InteresseCompra a ser retornado

        Returns:
            InteresseCompra atualizado

        Raises:
            InteresseCompraServiceError: Se o interesse não puder ser retornado
        """
        if not interesse.pode_retornar:
            raise InteresseCompraServiceError(
                f"Interesse #{interesse.pk} não pode retornar para Novo. Status atual: {interesse.get_status_display()}",
            )

        interesse.status = StatusInteresse.NOVO
        interesse.corretor = None
        interesse.save()

        return interesse


def get_corretores_ativos_emails():
    """Retorna lista de e-mails dos funcionários que são corretores ativos."""
    funcionarios = Funcionario.objects.filter(
        is_corretor=True, ativo=True
    ).select_related("usuario")
    return [f.email for f in funcionarios]


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
