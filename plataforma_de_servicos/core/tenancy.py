"""
Helpers de isolamento por empresa (tenant) para views fora do admin.
"""


def get_tenant_from_request(request):
    """Obtém o tenant do request."""
    return getattr(request, "tenant", None)


def filtrar_por_tenant(queryset, request, campo="empresa"):
    """Filtra pelo tenant; sem tenant, só superusuário vê tudo (fail-closed)."""
    tenant = get_tenant_from_request(request)
    if tenant:
        return queryset.filter(**{campo: tenant})
    if request.user.is_superuser:
        return queryset
    return queryset.none()
