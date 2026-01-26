from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.admin import TabularInline

from plataforma_de_servicos.vendas.models import ItemOrdemCompra
from plataforma_de_servicos.vendas.models import OrdemCompra
from plataforma_de_servicos.vendas.models import StatusOrdemCompra
from plataforma_de_servicos.vendas.services import OrdemCompraService
from plataforma_de_servicos.vendas.services import OrdemCompraServiceError


class ItemOrdemCompraInline(TabularInline):
    model = ItemOrdemCompra
    extra = 0
    readonly_fields = [
        "produto_nome",
        "variacao_info",
        "quantidade",
        "preco_unitario",
        "get_subtotal",
    ]
    fields = [
        "produto_nome",
        "variacao_info",
        "quantidade",
        "preco_unitario",
        "get_subtotal",
    ]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Subtotal")
    def get_subtotal(self, obj):
        return f"R$ {obj.subtotal:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@admin.register(OrdemCompra)
class OrdemCompraAdmin(ModelAdmin):
    list_display = [
        "numero",
        "nome_cliente",
        "corretor",
        "get_valor_total",
        "get_status_badge",
        "created",
        "data_aprovacao",
    ]
    list_display_links = ["numero", "nome_cliente"]
    list_filter = ["status", "corretor", "created", "data_aprovacao"]
    search_fields = ["numero", "nome_cliente", "email_cliente", "telefone_cliente"]
    autocomplete_fields = ["corretor", "aprovado_por"]
    readonly_fields = [
        "numero",
        "interesse",
        "nome_cliente",
        "email_cliente",
        "telefone_cliente",
        "valor_total",
        "aprovado_por",
        "data_aprovacao",
        "created",
        "modified",
    ]
    inlines = [ItemOrdemCompraInline]
    actions = ["action_aprovar", "action_faturar"]

    fieldsets = [
        (
            "Identificação",
            {
                "fields": ["numero", "interesse"],
            },
        ),
        (
            "Dados do Cliente",
            {
                "fields": ["nome_cliente", "email_cliente", "telefone_cliente"],
            },
        ),
        (
            "Valor",
            {
                "fields": ["valor_total"],
            },
        ),
        (
            "Status e Aprovação",
            {
                "fields": ["status", "corretor", "aprovado_por", "data_aprovacao", "motivo_rejeicao"],
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
            "Informações do Sistema",
            {
                "fields": ["created", "modified"],
                "classes": ["collapse"],
            },
        ),
    ]

    @admin.display(description="Valor Total")
    def get_valor_total(self, obj):
        return f"R$ {obj.valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @admin.display(description="Status")
    def get_status_badge(self, obj):
        colors = {
            StatusOrdemCompra.PENDENTE_APROVACAO: "#f59e0b",  # amber
            StatusOrdemCompra.APROVADA: "#10b981",  # green
            StatusOrdemCompra.REJEITADA: "#ef4444",  # red
            StatusOrdemCompra.FATURADA: "#3b82f6",  # blue
            StatusOrdemCompra.CONCLUIDA: "#6366f1",  # indigo
            StatusOrdemCompra.CANCELADA: "#6b7280",  # gray
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: 500;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.action(description="Aprovar ordens selecionadas")
    def action_aprovar(self, request, queryset):
        aprovadas = 0
        erros = []
        for ordem in queryset:
            try:
                OrdemCompraService.aprovar(ordem, request.user)
                aprovadas += 1
            except OrdemCompraServiceError as e:
                erros.append(f"{ordem.numero}: {str(e)}")

        if aprovadas:
            self.message_user(
                request,
                f"{aprovadas} ordem(ns) aprovada(s) com sucesso.",
                messages.SUCCESS,
            )
        if erros:
            self.message_user(
                request,
                f"Erros: {'; '.join(erros)}",
                messages.ERROR,
            )

    @admin.action(description="Faturar ordens selecionadas")
    def action_faturar(self, request, queryset):
        faturadas = 0
        erros = []
        for ordem in queryset:
            try:
                OrdemCompraService.faturar(ordem, request.user)
                faturadas += 1
            except OrdemCompraServiceError as e:
                erros.append(f"{ordem.numero}: {str(e)}")

        if faturadas:
            self.message_user(
                request,
                f"{faturadas} ordem(ns) faturada(s) com sucesso.",
                messages.SUCCESS,
            )
        if erros:
            self.message_user(
                request,
                f"Erros: {'; '.join(erros)}",
                messages.ERROR,
            )


# Admin para o site de gerentes (sem @admin.register)
class ItemOrdemCompraGerenteInline(TabularInline):
    model = ItemOrdemCompra
    extra = 0
    readonly_fields = [
        "produto_nome",
        "variacao_info",
        "quantidade",
        "preco_unitario",
        "get_subtotal",
    ]
    fields = [
        "produto_nome",
        "variacao_info",
        "quantidade",
        "preco_unitario",
        "get_subtotal",
    ]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Subtotal")
    def get_subtotal(self, obj):
        return f"R$ {obj.subtotal:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class OrdemCompraGerenteAdmin(ModelAdmin):
    list_display = [
        "numero",
        "nome_cliente",
        "corretor",
        "get_valor_total",
        "get_status_badge",
        "created",
        "data_aprovacao",
    ]
    list_display_links = ["numero", "nome_cliente"]
    list_filter = ["status", "corretor", "created", "data_aprovacao"]
    search_fields = ["numero", "nome_cliente", "email_cliente", "telefone_cliente"]
    autocomplete_fields = ["corretor"]
    readonly_fields = [
        "numero",
        "interesse",
        "nome_cliente",
        "email_cliente",
        "telefone_cliente",
        "valor_total",
        "aprovado_por",
        "data_aprovacao",
        "created",
        "modified",
    ]
    inlines = [ItemOrdemCompraGerenteInline]
    actions = ["action_aprovar", "action_faturar"]

    fieldsets = [
        (
            "Identificação",
            {
                "fields": ["numero", "interesse"],
            },
        ),
        (
            "Dados do Cliente",
            {
                "fields": ["nome_cliente", "email_cliente", "telefone_cliente"],
            },
        ),
        (
            "Valor",
            {
                "fields": ["valor_total"],
            },
        ),
        (
            "Status e Aprovação",
            {
                "fields": ["status", "corretor", "aprovado_por", "data_aprovacao", "motivo_rejeicao"],
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
            "Informações do Sistema",
            {
                "fields": ["created", "modified"],
                "classes": ["collapse"],
            },
        ),
    ]

    @admin.display(description="Valor Total")
    def get_valor_total(self, obj):
        return f"R$ {obj.valor_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @admin.display(description="Status")
    def get_status_badge(self, obj):
        colors = {
            StatusOrdemCompra.PENDENTE_APROVACAO: "#f59e0b",  # amber
            StatusOrdemCompra.APROVADA: "#10b981",  # green
            StatusOrdemCompra.REJEITADA: "#ef4444",  # red
            StatusOrdemCompra.FATURADA: "#3b82f6",  # blue
            StatusOrdemCompra.CONCLUIDA: "#6366f1",  # indigo
            StatusOrdemCompra.CANCELADA: "#6b7280",  # gray
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: 500;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.action(description="Aprovar ordens selecionadas")
    def action_aprovar(self, request, queryset):
        aprovadas = 0
        erros = []
        for ordem in queryset:
            try:
                OrdemCompraService.aprovar(ordem, request.user)
                aprovadas += 1
            except OrdemCompraServiceError as e:
                erros.append(f"{ordem.numero}: {str(e)}")

        if aprovadas:
            self.message_user(
                request,
                f"{aprovadas} ordem(ns) aprovada(s) com sucesso.",
                messages.SUCCESS,
            )
        if erros:
            self.message_user(
                request,
                f"Erros: {'; '.join(erros)}",
                messages.ERROR,
            )

    @admin.action(description="Faturar ordens selecionadas")
    def action_faturar(self, request, queryset):
        faturadas = 0
        erros = []
        for ordem in queryset:
            try:
                OrdemCompraService.faturar(ordem, request.user)
                faturadas += 1
            except OrdemCompraServiceError as e:
                erros.append(f"{ordem.numero}: {str(e)}")

        if faturadas:
            self.message_user(
                request,
                f"{faturadas} ordem(ns) faturada(s) com sucesso.",
                messages.SUCCESS,
            )
        if erros:
            self.message_user(
                request,
                f"Erros: {'; '.join(erros)}",
                messages.ERROR,
            )
