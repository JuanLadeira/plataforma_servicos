def marcar_padroes(Inventario):  # noqa: N803
    """Marca um depósito padrão em cada empresa que ainda não tem.

    Prefere o inventário ativo exibido na vitrine mais antigo; sem vitrine, o ativo mais antigo.
    Recebe o model como parâmetro para funcionar com o model histórico da migration.
    """
    empresas_com_padrao = Inventario.objects.filter(padrao=True).values("empresa_id")
    candidatos = (
        Inventario.objects.filter(is_ativo=True, empresa__isnull=False)
        .exclude(empresa_id__in=empresas_com_padrao)
        .order_by("empresa_id", "-exibir_na_vitrine", "created", "pk")
    )
    vistas = set()
    for inventario in candidatos:
        if inventario.empresa_id in vistas:
            continue
        vistas.add(inventario.empresa_id)
        Inventario.objects.filter(pk=inventario.pk).update(padrao=True)
