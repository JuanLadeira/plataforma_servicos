from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import VariacaoProduto


@receiver(post_save, sender=VariacaoProduto)
def gerar_sku_para_variacao(sender, instance, created, **kwargs):
    """
    Gera um SKU para a variação após ela ser salva, se ainda não tiver um.
    """
    if not instance.sku:
        instance.gerar_sku()