from django.db.models.signals import m2m_changed
from django.dispatch import receiver


@receiver(m2m_changed, sender='produto.VariacaoProduto_valores')
def auto_gerar_sku(sender, instance, action, **kwargs):
    """
    Gera ou atualiza o SKU após os valores M2M serem modificados.

    O SKU é composto pelo slug do produto + IDs dos valores de atributo ordenados.
    É regenerado sempre que a relação M2M muda para manter consistência.
    """
    if action in ['post_add', 'post_remove', 'post_clear']:
        # Importar aqui para evitar circular import
        from plataforma_de_servicos.produto.models.atributos import VariacaoProduto

        if instance.pk and instance.valores.exists():
            # Regenera o SKU com todos os valores atuais
            valores_ids = sorted(
                instance.valores.only('id').values_list("id", flat=True)
            )
            produto_slug = instance.produto.slug if hasattr(instance.produto, 'slug') else str(instance.produto.pk)
            new_sku = f"{produto_slug}-" + "-".join(map(str, valores_ids))

            # Só atualiza se mudou
            if instance.sku != new_sku:
                VariacaoProduto.objects.filter(pk=instance.pk).update(sku=new_sku)
                instance.sku = new_sku  # Atualiza a instância em memória também
