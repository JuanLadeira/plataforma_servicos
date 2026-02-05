from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import InventarioSaldo


@receiver(post_save, sender=InventarioSaldo)
def atualizar_disponibilidade_produto(sender, instance, **kwargs):
    """
    Atualiza o campo 'disponivel' do produto com base no saldo do inventário.
    """
    produto = instance.produto

    # Verifica se existe algum saldo em inventário que justifique a exibição na vitrine
    is_disponivel_na_vitrine = InventarioSaldo.objects.filter(
        produto=produto,
        quantidade__gt=0,
        inventario__is_ativo=True,
        inventario__exibir_na_vitrine=True,
    ).exists()

    # Atualiza o produto apenas se o status de disponibilidade mudou
    if produto.disponivel != is_disponivel_na_vitrine:
        produto.disponivel = is_disponivel_na_vitrine
        produto.save(update_fields=["disponivel"])
