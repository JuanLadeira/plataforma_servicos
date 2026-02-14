"""
Admin para gestão de comissões.
"""
from django.contrib import admin
from django.utils import timezone
from unfold.admin import ModelAdmin, TabularInline

from plataforma_de_servicos.core.admin.mixins import TenantAwareAdminMixin
from plataforma_de_servicos.vendas.models import (
    Comissao,
    ComissaoCategoria,
    ComissaoVendedor,
    ConfiguracaoComissao,
    StatusComissao,
)


# ============================================
# Inlines para Configuração de Comissão
# ============================================


class ComissaoCategoriaInline(TabularInline):
    """Inline para comissões por categoria."""

    model = ComissaoCategoria
    extra = 1
    autocomplete_fields = ["categoria"]


class ComissaoVendedorInline(TabularInline):
    """Inline para comissões por vendedor."""

    model = ComissaoVendedor
    extra = 1
    autocomplete_fields = ["funcionario"]


# ============================================
# Admin para Gerentes (acesso completo)
# ============================================


class ComissaoGerenteAdmin(TenantAwareAdminMixin, ModelAdmin):
    """Admin de comissões para gerentes."""

    list_display = [
        "ordem",
        "funcionario",
        "percentual",
        "valor_base",
        "valor_comissao",
        "status",
        "data_pagamento",
        "created",
    ]
    list_filter = ["status", "created", "data_pagamento"]
    search_fields = [
        "ordem__numero",
        "funcionario__usuario__name",
        "funcionario__usuario__email",
    ]
    readonly_fields = ["created", "modified"]
    autocomplete_fields = ["ordem", "funcionario"]

    fieldsets = [
        (
            "Ordem e Vendedor",
            {
                "fields": ["ordem", "funcionario"],
            },
        ),
        (
            "Valores",
            {
                "fields": ["percentual", "valor_base", "valor_comissao"],
            },
        ),
        (
            "Status e Pagamento",
            {
                "fields": ["status", "data_aprovacao", "data_pagamento"],
            },
        ),
        (
            "Observações",
            {
                "fields": ["observacoes"],
                "classes": ["collapse"],
            },
        ),
        (
            "Datas",
            {
                "fields": ["created", "modified"],
                "classes": ["collapse"],
            },
        ),
    ]

    actions = ["aprovar_comissoes", "marcar_como_paga"]

    @admin.action(description="Aprovar comissões selecionadas")
    def aprovar_comissoes(self, request, queryset):
        """Aprova as comissões selecionadas."""
        count = 0
        for comissao in queryset.filter(status=StatusComissao.PENDENTE):
            comissao.status = StatusComissao.APROVADA
            comissao.data_aprovacao = timezone.now().date()
            comissao.save()
            count += 1
        self.message_user(request, f"{count} comissão(ões) aprovada(s).")

    @admin.action(description="Marcar como paga")
    def marcar_como_paga(self, request, queryset):
        """Marca as comissões como pagas."""
        count = 0
        for comissao in queryset.filter(status=StatusComissao.APROVADA):
            comissao.status = StatusComissao.PAGA
            comissao.data_pagamento = timezone.now().date()
            comissao.save()
            count += 1
        self.message_user(request, f"{count} comissão(ões) marcada(s) como paga(s).")


class ConfiguracaoComissaoGerenteAdmin(TenantAwareAdminMixin, ModelAdmin):
    """Admin de configuração de comissões para gerentes."""

    list_display = ["empresa", "percentual_padrao", "aplica_sobre_desconto"]
    search_fields = ["empresa__nome"]
    inlines = [ComissaoCategoriaInline, ComissaoVendedorInline]

    fieldsets = [
        (
            "Configuração Geral",
            {
                "fields": ["percentual_padrao", "aplica_sobre_desconto"],
            },
        ),
    ]

    def has_add_permission(self, request):
        """Só permite uma configuração por empresa (via tenant)."""
        tenant = getattr(request, "tenant", None)
        if tenant and ConfiguracaoComissao.objects.filter(empresa=tenant).exists():
            return False
        return super().has_add_permission(request)


# ============================================
# Admin para Vendedores (acesso limitado)
# ============================================


class ComissaoVendedorAdminReadOnly(TenantAwareAdminMixin, ModelAdmin):
    """
    Admin de comissões para vendedores.

    Vendedores podem apenas visualizar suas próprias comissões.
    """

    list_display = [
        "ordem",
        "percentual",
        "valor_base",
        "valor_comissao",
        "status",
        "data_pagamento",
        "created",
    ]
    list_filter = ["status", "created"]
    search_fields = ["ordem__numero"]
    readonly_fields = [
        "ordem",
        "funcionario",
        "percentual",
        "valor_base",
        "valor_comissao",
        "status",
        "data_aprovacao",
        "data_pagamento",
        "observacoes",
        "created",
        "modified",
    ]

    def get_queryset(self, request):
        """Filtra para mostrar apenas comissões do vendedor logado."""
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        if hasattr(request.user, "funcionario"):
            funcionario = request.user.funcionario

            # Gerentes veem todas as comissões da empresa
            if funcionario.is_gerente:
                return qs

            # Vendedores veem apenas suas comissões
            return qs.filter(funcionario=funcionario)

        return qs.none()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
