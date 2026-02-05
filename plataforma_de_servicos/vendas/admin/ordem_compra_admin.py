from django.contrib import admin
from django.contrib import messages
from django.http import HttpRequest
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.admin import TabularInline
from unfold.decorators import action

from plataforma_de_servicos.core.admin.mixins import TenantAwareAdminMixin
from plataforma_de_servicos.core.admin.mixins import TenantAwareInlineMixin
from plataforma_de_servicos.produto.models import VariacaoProduto
from plataforma_de_servicos.vendas.admin.forms import CancelamentoOrdemForm
from plataforma_de_servicos.vendas.admin.forms import RejeicaoOrdemForm
from plataforma_de_servicos.vendas.models import ItemOrdemCompra
from plataforma_de_servicos.vendas.models import OrdemCompra
from plataforma_de_servicos.vendas.models import StatusOrdemCompra
from plataforma_de_servicos.vendas.services import OrdemCompraService
from plataforma_de_servicos.vendas.services import OrdemCompraServiceError


class ItemOrdemCompraInline(TabularInline):
    """Inline para admin padrão - sem autocomplete (modelos não registrados aqui)."""

    model = ItemOrdemCompra
    extra = 1

    @admin.display(description="Subtotal")
    def get_subtotal(self, obj):
        if obj and obj.pk:
            return f"R$ {obj.subtotal:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return "-"

    def get_fields(self, request, obj=None):
        """Mostra campos editáveis se ordem pendente, senão readonly."""
        if obj and obj.status == StatusOrdemCompra.PENDENTE_APROVACAO:
            return ["produto", "variacao", "produto_nome", "variacao_info", "quantidade", "preco_unitario", "get_subtotal"]
        return ["produto_nome", "variacao_info", "quantidade", "preco_unitario", "get_subtotal"]

    def get_readonly_fields(self, request, obj=None):
        """Campos readonly dependem do status da ordem."""
        if obj and obj.status == StatusOrdemCompra.PENDENTE_APROVACAO:
            return ["get_subtotal"]
        return ["produto_nome", "variacao_info", "quantidade", "preco_unitario", "get_subtotal"]

    def has_add_permission(self, request, obj=None):
        """Permite adicionar itens apenas se ordem pendente."""
        if obj and obj.status != StatusOrdemCompra.PENDENTE_APROVACAO:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        """Permite deletar itens apenas se ordem pendente."""
        if obj and obj.status != StatusOrdemCompra.PENDENTE_APROVACAO:
            return False
        return True


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
            "Identificacao",
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
            "Status e Aprovacao",
            {
                "fields": ["status", "corretor", "aprovado_por", "data_aprovacao", "motivo_rejeicao"],
            },
        ),
        (
            "Observacoes",
            {
                "fields": ["observacoes"],
                "classes": ["collapse"],
            },
        ),
        (
            "Informacoes do Sistema",
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
                OrdemCompraService.faturar(ordem)
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


# ============================================================
# Admin para o site de gerentes (sem @admin.register)
# ============================================================


class ItemOrdemCompraGerenteInline(TabularInline):
    model = ItemOrdemCompra
    extra = 1
    autocomplete_fields = ["produto", "variacao"]

    @admin.display(description="Subtotal")
    def get_subtotal(self, obj):
        if obj and obj.pk:
            return f"R$ {obj.subtotal:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return "-"

    def get_fields(self, request, obj=None):
        """Mostra campos editáveis se ordem pendente, senão readonly."""
        if obj and obj.status == StatusOrdemCompra.PENDENTE_APROVACAO:
            return ["produto", "variacao", "produto_nome", "variacao_info", "quantidade", "preco_unitario", "get_subtotal"]
        return ["produto_nome", "variacao_info", "quantidade", "preco_unitario", "get_subtotal"]

    def get_readonly_fields(self, request, obj=None):
        """Campos readonly dependem do status da ordem."""
        if obj and obj.status == StatusOrdemCompra.PENDENTE_APROVACAO:
            return ["get_subtotal"]
        return ["produto_nome", "variacao_info", "quantidade", "preco_unitario", "get_subtotal"]

    def has_add_permission(self, request, obj=None):
        """Permite adicionar itens apenas se ordem pendente."""
        if obj and obj.status != StatusOrdemCompra.PENDENTE_APROVACAO:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        """Permite deletar itens apenas se ordem pendente."""
        if obj and obj.status != StatusOrdemCompra.PENDENTE_APROVACAO:
            return False
        return True

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "variacao":
            kwargs["queryset"] = VariacaoProduto.objects.select_related(
                "produto"
            ).prefetch_related("valores", "valores__atributo")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class OrdemCompraGerenteAdmin(TenantAwareAdminMixin, ModelAdmin):
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
        "status",
        "aprovado_por",
        "data_aprovacao",
        "created",
        "modified",
    ]
    inlines = [ItemOrdemCompraGerenteInline]
    actions = ["action_aprovar", "action_faturar"]
    actions_detail = [
        "detail_aprovar",
        "detail_rejeitar",
        "detail_faturar",
        "detail_concluir",
        "detail_cancelar",
    ]

    fieldsets = [
        (
            "Identificacao",
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
            "Status e Aprovacao",
            {
                "fields": ["status", "corretor", "aprovado_por", "data_aprovacao", "motivo_rejeicao"],
            },
        ),
        (
            "Observacoes",
            {
                "fields": ["observacoes"],
                "classes": ["collapse"],
            },
        ),
        (
            "Informacoes do Sistema",
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
                OrdemCompraService.faturar(ordem)
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

    # ========================================
    # Permissoes condicionais para acoes de detalhe
    # ========================================

    def has_detail_aprovar_permission(self, request: HttpRequest, object_id: int) -> bool:
        """Verifica se pode aprovar a ordem."""
        ordem = OrdemCompra.objects.filter(pk=object_id).first()
        return ordem is not None and ordem.pode_aprovar

    def has_detail_rejeitar_permission(self, request: HttpRequest, object_id: int) -> bool:
        """Verifica se pode rejeitar a ordem."""
        ordem = OrdemCompra.objects.filter(pk=object_id).first()
        return ordem is not None and ordem.pode_rejeitar

    def has_detail_faturar_permission(self, request: HttpRequest, object_id: int) -> bool:
        """Verifica se pode faturar a ordem."""
        ordem = OrdemCompra.objects.filter(pk=object_id).first()
        return ordem is not None and ordem.pode_faturar

    def has_detail_concluir_permission(self, request: HttpRequest, object_id: int) -> bool:
        """Verifica se pode concluir a ordem."""
        ordem = OrdemCompra.objects.filter(pk=object_id).first()
        return ordem is not None and ordem.pode_concluir

    def has_detail_cancelar_permission(self, request: HttpRequest, object_id: int) -> bool:
        """Verifica se pode cancelar a ordem."""
        ordem = OrdemCompra.objects.filter(pk=object_id).first()
        return ordem is not None and ordem.pode_cancelar

    # ========================================
    # Acoes de detalhe (botoes no formulario)
    # ========================================

    @action(
        description="Aprovar",
        url_path="aprovar",
        permissions=["detail_aprovar"],
    )
    def detail_aprovar(self, request: HttpRequest, object_id: int) -> HttpResponse:
        """Aprova a ordem de compra."""
        ordem = get_object_or_404(OrdemCompra, pk=object_id)
        try:
            OrdemCompraService.aprovar(ordem, request.user)
            self.message_user(
                request,
                f"Ordem {ordem.numero} aprovada com sucesso.",
                messages.SUCCESS,
            )
        except OrdemCompraServiceError as e:
            self.message_user(request, str(e), messages.ERROR)
        return redirect(
            reverse("gerentes:vendas_ordemcompra_change", args=[object_id])
        )

    @action(
        description="Rejeitar",
        url_path="rejeitar",
        permissions=["detail_rejeitar"],
    )
    def detail_rejeitar(self, request: HttpRequest, object_id: int) -> HttpResponse:
        """Rejeita a ordem de compra (requer motivo)."""
        ordem = get_object_or_404(OrdemCompra, pk=object_id)
        form = RejeicaoOrdemForm(request.POST or None)

        if request.method == "POST" and form.is_valid():
            try:
                OrdemCompraService.rejeitar(
                    ordem, request.user, form.cleaned_data["motivo"]
                )
                self.message_user(
                    request,
                    f"Ordem {ordem.numero} rejeitada.",
                    messages.WARNING,
                )
                return redirect(
                    reverse("gerentes:vendas_ordemcompra_change", args=[object_id])
                )
            except OrdemCompraServiceError as e:
                self.message_user(request, str(e), messages.ERROR)

        return render(
            request,
            "admin/vendas/ordemcompra/action_rejeitar.html",
            {
                "form": form,
                "object": ordem,
                "opts": self.model._meta,
                "site_header": self.admin_site.site_header,
            },
        )

    @action(
        description="Faturar",
        url_path="faturar",
        permissions=["detail_faturar"],
    )
    def detail_faturar(self, request: HttpRequest, object_id: int) -> HttpResponse:
        """Marca a ordem como faturada."""
        ordem = get_object_or_404(OrdemCompra, pk=object_id)
        try:
            OrdemCompraService.faturar(ordem)
            self.message_user(
                request,
                f"Ordem {ordem.numero} faturada com sucesso.",
                messages.SUCCESS,
            )
        except OrdemCompraServiceError as e:
            self.message_user(request, str(e), messages.ERROR)
        return redirect(
            reverse("gerentes:vendas_ordemcompra_change", args=[object_id])
        )

    @action(
        description="Concluir",
        url_path="concluir",
        permissions=["detail_concluir"],
    )
    def detail_concluir(self, request: HttpRequest, object_id: int) -> HttpResponse:
        """Marca a ordem como concluida."""
        ordem = get_object_or_404(OrdemCompra, pk=object_id)
        try:
            OrdemCompraService.concluir(ordem)
            self.message_user(
                request,
                f"Ordem {ordem.numero} concluida com sucesso.",
                messages.SUCCESS,
            )
        except OrdemCompraServiceError as e:
            self.message_user(request, str(e), messages.ERROR)
        return redirect(
            reverse("gerentes:vendas_ordemcompra_change", args=[object_id])
        )

    @action(
        description="Cancelar",
        url_path="cancelar",
        permissions=["detail_cancelar"],
    )
    def detail_cancelar(self, request: HttpRequest, object_id: int) -> HttpResponse:
        """Cancela a ordem de compra (motivo opcional)."""
        ordem = get_object_or_404(OrdemCompra, pk=object_id)
        form = CancelamentoOrdemForm(request.POST or None)

        if request.method == "POST" and form.is_valid():
            try:
                OrdemCompraService.cancelar(ordem, form.cleaned_data.get("motivo", ""))
                self.message_user(
                    request,
                    f"Ordem {ordem.numero} cancelada.",
                    messages.WARNING,
                )
                return redirect(
                    reverse("gerentes:vendas_ordemcompra_change", args=[object_id])
                )
            except OrdemCompraServiceError as e:
                self.message_user(request, str(e), messages.ERROR)

        return render(
            request,
            "admin/vendas/ordemcompra/action_cancelar.html",
            {
                "form": form,
                "object": ordem,
                "opts": self.model._meta,
                "site_header": self.admin_site.site_header,
            },
        )
