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
from plataforma_de_servicos.corretor.admin.forms import DescarteInteresseForm
from plataforma_de_servicos.corretor.models import InteresseCompra
from plataforma_de_servicos.corretor.models import ItemInteresse
from plataforma_de_servicos.corretor.models import StatusInteresse
from plataforma_de_servicos.corretor.services import InteresseCompraService
from plataforma_de_servicos.corretor.services import InteresseCompraServiceError


class ItemInteresseGerenteInline(TabularInline):
    model = ItemInteresse
    extra = 0
    readonly_fields = ["produto_nome", "variacao_info", "quantidade", "preco_unitario"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class InteresseCompraGerenteAdmin(TenantAwareAdminMixin, ModelAdmin):
    list_display = [
        "numero",
        "nome_cliente",
        "email_cliente",
        "telefone_cliente",
        "valor_total",
        "get_status_badge",
        "corretor",
        "created",
    ]
    list_display_links = ["numero", "nome_cliente"]
    list_filter = ["status", "corretor", "created"]
    search_fields = ["numero", "nome_cliente", "email_cliente", "telefone_cliente"]
    autocomplete_fields = ["corretor"]
    readonly_fields = [
        "numero",
        "nome_cliente",
        "email_cliente",
        "telefone_cliente",
        "mensagem",
        "valor_total",
        "status",
        "created",
        "modified",
    ]
    inlines = [ItemInteresseGerenteInline]
    actions_detail = [
        "detail_atender",
        "detail_converter",
        "detail_descartar",
        "detail_retornar",
    ]

    fieldsets = [
        (
            "Identificação",
            {
                "fields": ["numero"],
            },
        ),
        (
            "Dados do Cliente",
            {
                "fields": ["nome_cliente", "email_cliente", "telefone_cliente", "mensagem"],
            },
        ),
        (
            "Valor",
            {
                "fields": ["valor_total"],
            },
        ),
        (
            "Atendimento",
            {
                "fields": ["status", "corretor"],
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

    @admin.display(description="Status")
    def get_status_badge(self, obj):
        colors = {
            StatusInteresse.NOVO: "#3b82f6",  # blue
            StatusInteresse.EM_ATENDIMENTO: "#f59e0b",  # amber
            StatusInteresse.CONVERTIDO: "#10b981",  # green
            StatusInteresse.DESCARTADO: "#6b7280",  # gray
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: 500;">{}</span>',
            color,
            obj.get_status_display(),
        )

    def get_readonly_fields(self, request, obj=None):
        """Permite editar corretor se superusuário ou se interesse estiver em atendimento."""
        readonly = list(self.readonly_fields)
        # Superusuários podem sempre editar o corretor
        if request.user.is_superuser:
            return readonly
        # Usuários normais só podem editar se status for EM_ATENDIMENTO
        if obj and obj.status != StatusInteresse.EM_ATENDIMENTO:
            readonly.append("corretor")
        return readonly

    # ========================================
    # Permissões condicionais para ações de detalhe
    # ========================================

    def has_detail_atender_permission(self, request: HttpRequest, object_id: int) -> bool:
        """Verifica se pode iniciar atendimento."""
        interesse = InteresseCompra.objects.filter(pk=object_id).first()
        return interesse is not None and interesse.pode_atender

    def has_detail_converter_permission(self, request: HttpRequest, object_id: int) -> bool:
        """Verifica se pode converter para ordem."""
        interesse = InteresseCompra.objects.filter(pk=object_id).first()
        return interesse is not None and interesse.pode_converter

    def has_detail_descartar_permission(self, request: HttpRequest, object_id: int) -> bool:
        """Verifica se pode descartar."""
        interesse = InteresseCompra.objects.filter(pk=object_id).first()
        return interesse is not None and interesse.pode_descartar

    def has_detail_retornar_permission(self, request: HttpRequest, object_id: int) -> bool:
        """Verifica se pode retornar para novo."""
        interesse = InteresseCompra.objects.filter(pk=object_id).first()
        return interesse is not None and interesse.pode_retornar

    # ========================================
    # Ações de detalhe (botões no formulário)
    # ========================================

    @action(
        description="Atender",
        url_path="atender",
        permissions=["detail_atender"],
    )
    def detail_atender(self, request: HttpRequest, object_id: int) -> HttpResponse:
        """Inicia o atendimento do interesse."""
        interesse = get_object_or_404(InteresseCompra, pk=object_id)

        # Verifica se o usuário é um funcionário com permissão de corretor
        funcionario = getattr(request.user, "funcionario", None)
        if not funcionario or not funcionario.is_corretor:
            self.message_user(
                request,
                "Você precisa ser um corretor para atender interesses. "
                "Solicite ao administrador que marque seu usuário como corretor.",
                messages.ERROR,
            )
            return redirect(
                reverse("gerentes:corretor_interessecompra_change", args=[object_id])
            )

        try:
            InteresseCompraService.atender(interesse, funcionario)
            self.message_user(
                request,
                f"Interesse #{interesse.pk} está agora em atendimento.",
                messages.SUCCESS,
            )
        except InteresseCompraServiceError as e:
            self.message_user(request, str(e), messages.ERROR)

        return redirect(
            reverse("gerentes:corretor_interessecompra_change", args=[object_id])
        )

    @action(
        description="Converter",
        url_path="converter",
        permissions=["detail_converter"],
    )
    def detail_converter(self, request: HttpRequest, object_id: int) -> HttpResponse:
        """Converte o interesse em ordem de compra."""
        interesse = get_object_or_404(InteresseCompra, pk=object_id)

        try:
            InteresseCompraService.converter(interesse)
            self.message_user(
                request,
                f"Interesse #{interesse.pk} convertido com sucesso! Uma ordem de compra foi criada.",
                messages.SUCCESS,
            )
        except InteresseCompraServiceError as e:
            self.message_user(request, str(e), messages.ERROR)

        return redirect(
            reverse("gerentes:corretor_interessecompra_change", args=[object_id])
        )

    @action(
        description="Descartar",
        url_path="descartar",
        permissions=["detail_descartar"],
    )
    def detail_descartar(self, request: HttpRequest, object_id: int) -> HttpResponse:
        """Descarta o interesse (requer motivo opcional)."""
        interesse = get_object_or_404(InteresseCompra, pk=object_id)
        form = DescarteInteresseForm(request.POST or None)

        if request.method == "POST" and form.is_valid():
            try:
                InteresseCompraService.descartar(
                    interesse, form.cleaned_data.get("motivo", "")
                )
                self.message_user(
                    request,
                    f"Interesse #{interesse.pk} foi descartado.",
                    messages.WARNING,
                )
                return redirect(
                    reverse("gerentes:corretor_interessecompra_change", args=[object_id])
                )
            except InteresseCompraServiceError as e:
                self.message_user(request, str(e), messages.ERROR)

        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "object": interesse,
            "opts": self.model._meta,
            "title": f"Descartar Interesse {interesse.numero or interesse.pk}",
        }
        return render(
            request,
            "admin/corretor/interessecompra/action_descartar.html",
            context,
        )

    @action(
        description="Retornar",
        url_path="retornar",
        permissions=["detail_retornar"],
    )
    def detail_retornar(self, request: HttpRequest, object_id: int) -> HttpResponse:
        """Retorna o interesse para status Novo."""
        interesse = get_object_or_404(InteresseCompra, pk=object_id)

        try:
            InteresseCompraService.retornar(interesse)
            self.message_user(
                request,
                f"Interesse #{interesse.pk} retornou para status Novo.",
                messages.INFO,
            )
        except InteresseCompraServiceError as e:
            self.message_user(request, str(e), messages.ERROR)

        return redirect(
            reverse("gerentes:corretor_interessecompra_change", args=[object_id])
        )
