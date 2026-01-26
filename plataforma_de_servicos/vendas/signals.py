import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from plataforma_de_servicos.corretor.models import InteresseCompra
from plataforma_de_servicos.corretor.models import StatusInteresse
from plataforma_de_servicos.vendas.services import OrdemCompraService
from plataforma_de_servicos.vendas.services import OrdemCompraServiceError

logger = logging.getLogger(__name__)


@receiver(post_save, sender=InteresseCompra)
def criar_ordem_ao_converter(sender, instance, **kwargs):
    """
    Cria automaticamente uma OrdemCompra quando um InteresseCompra
    é marcado como CONVERTIDO.
    """
    if instance.status != StatusInteresse.CONVERTIDO:
        return

    # Verifica se já existe uma ordem associada
    if hasattr(instance, "ordem_compra"):
        try:
            # Força a query para verificar se realmente existe
            _ = instance.ordem_compra.pk
            logger.debug(
                "Interesse #%s já possui ordem de compra associada.",
                instance.pk,
            )
            return
        except Exception:
            # RelatedObjectDoesNotExist - ordem não existe ainda
            pass

    try:
        ordem = OrdemCompraService.criar_ordem_de_interesse(instance)
        logger.info(
            "Ordem de compra %s criada automaticamente para interesse #%s",
            ordem.numero,
            instance.pk,
        )
    except OrdemCompraServiceError as e:
        logger.warning(
            "Não foi possível criar ordem de compra para interesse #%s: %s",
            instance.pk,
            str(e),
        )
