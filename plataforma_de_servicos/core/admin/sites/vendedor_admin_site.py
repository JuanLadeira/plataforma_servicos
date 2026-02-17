"""
Portal administrativo para vendedores.

Este portal oferece funcionalidades limitadas para vendedores,
incluindo visualização de interesses, ordens de compra (suas) e catálogo.
"""
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
from unfold.sites import UnfoldAdminSite

from plataforma_de_servicos.core.admin.mixins import TenantAwareAdminMixin
from plataforma_de_servicos.corretor.admin.forms import DescarteInteresseForm
from plataforma_de_servicos.corretor.models import InteresseCompra
from plataforma_de_servicos.corretor.models import ItemInteresse
from plataforma_de_servicos.corretor.models import StatusInteresse
from plataforma_de_servicos.corretor.services import InteresseCompraService
from plataforma_de_servicos.corretor.services import InteresseCompraServiceError
from plataforma_de_servicos.empresa.models import Empresa
from plataforma_de_servicos.produto.models.categoria_model import Categoria
from plataforma_de_servicos.produto.models.produto_model import Produto
from plataforma_de_servicos.users.models import PapelFuncionario
from plataforma_de_servicos.vendas.admin.comissao_admin import ComissaoVendedorAdminReadOnly
from plataforma_de_servicos.vendas.models import Comissao, OrdemCompra


class ProdutoVendedorAdmin(TenantAwareAdminMixin, ModelAdmin):
    """
    Admin de produtos para vendedores.

    Vendedores podem apenas visualizar produtos, não editar.
    """

    list_display = ["produto", "categoria", "preco", "disponivel"]
    list_filter = ["categoria", "disponivel"]
    search_fields = ["produto", "descricao"]
    readonly_fields = [
        "produto",
        "slug",
        "categoria",
        "preco",
        "descricao",
        "disponivel",
        "empresa",
    ]

    def has_add_permission(self, request):
        """Vendedores não podem adicionar produtos."""
        return False

    def has_change_permission(self, request, obj=None):
        """Vendedores não podem editar produtos."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Vendedores não podem excluir produtos."""
        return False


class CategoriaVendedorAdmin(TenantAwareAdminMixin, ModelAdmin):
    """
    Admin de categorias para vendedores.

    Vendedores podem apenas visualizar categorias.
    """

    list_display = ["categoria", "slug"]
    search_fields = ["categoria"]
    readonly_fields = ["categoria", "slug", "empresa"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ItemInteresseVendedorInline(TabularInline):
    """Inline para mostrar os itens do interesse de compra."""

    model = ItemInteresse
    extra = 0
    readonly_fields = ["produto_nome", "variacao_info", "quantidade", "preco_unitario"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class InteresseCompraVendedorAdmin(TenantAwareAdminMixin, ModelAdmin):
    """
    Admin de interesses de compra para vendedores.

    Vendedores podem ver e atender interesses atribuídos a eles.
    """

    list_display = [
        "numero",
        "nome_cliente",
        "telefone_cliente",
        "valor_total",
        "get_status_badge",
        "corretor",
        "created",
    ]
    list_display_links = ["numero", "nome_cliente"]
    list_filter = ["status", "created"]
    search_fields = [
        "nome_cliente",
        "telefone_cliente",
        "email_cliente",
        "numero",
    ]
    readonly_fields = [
        "numero",
        "nome_cliente",
        "telefone_cliente",
        "email_cliente",
        "mensagem",
        "valor_total",
        "status",
        "corretor",
        "created",
        "modified",
    ]
    inlines = [ItemInteresseVendedorInline]
    actions_detail = [
        "detail_atender",
        "detail_converter",
        "detail_descartar",
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

    def get_queryset(self, request):
        """Filtra para mostrar apenas interesses do vendedor logado ou novos."""
        qs = super().get_queryset(request)

        # Superusuários veem tudo
        if request.user.is_superuser:
            return qs

        # Funcionários
        if hasattr(request.user, "funcionario"):
            funcionario = request.user.funcionario

            # Gerentes e admins veem todos os interesses da empresa
            if funcionario.is_gerente:
                return qs

            # Vendedores veem interesses NOVOS (disponíveis) ou atribuídos a eles
            from django.db.models import Q
            return qs.filter(
                Q(status=StatusInteresse.NOVO) |
                Q(corretor=funcionario)
            )

        return qs.none()

    def has_add_permission(self, request):
        """Vendedores não podem criar interesses manualmente."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Vendedores não podem excluir interesses."""
        return False

    def has_change_permission(self, request, obj=None):
        """Vendedores podem ver detalhes mas não editar campos diretamente."""
        return True

    # ========================================
    # Permissões condicionais para ações
    # ========================================

    def has_detail_atender_permission(self, request: HttpRequest, object_id: int) -> bool:
        """Verifica se pode iniciar atendimento."""
        interesse = InteresseCompra.objects.filter(pk=object_id).first()
        return interesse is not None and interesse.pode_atender

    def has_detail_converter_permission(self, request: HttpRequest, object_id: int) -> bool:
        """Verifica se pode converter para ordem."""
        interesse = InteresseCompra.objects.filter(pk=object_id).first()
        if not interesse or not interesse.pode_converter:
            return False

        # Vendedor só pode converter se for o corretor do interesse
        funcionario = getattr(request.user, "funcionario", None)
        if funcionario and interesse.corretor_id == funcionario.pk:
            return True

        return request.user.is_superuser

    def has_detail_descartar_permission(self, request: HttpRequest, object_id: int) -> bool:
        """Verifica se pode descartar."""
        interesse = InteresseCompra.objects.filter(pk=object_id).first()
        if not interesse or not interesse.pode_descartar:
            return False

        # Vendedor só pode descartar se for o corretor do interesse
        funcionario = getattr(request.user, "funcionario", None)
        if funcionario and interesse.corretor_id == funcionario.pk:
            return True

        return request.user.is_superuser

    # ========================================
    # Ações de detalhe
    # ========================================

    @action(
        description="Atender",
        url_path="atender",
        permissions=["detail_atender"],
    )
    def detail_atender(self, request: HttpRequest, object_id: int) -> HttpResponse:
        """Inicia o atendimento do interesse, atribuindo ao vendedor logado."""
        interesse = get_object_or_404(InteresseCompra, pk=object_id)

        # Obtém o vendedor logado
        funcionario = getattr(request.user, "funcionario", None)
        if not funcionario:
            self.message_user(
                request,
                "Você precisa ser um funcionário para atender interesses.",
                messages.ERROR,
            )
            return redirect(
                reverse("vendedores:corretor_interessecompra_change", args=[object_id])
            )

        try:
            # Atribui automaticamente ao vendedor logado
            InteresseCompraService.atender(interesse, funcionario)
            self.message_user(
                request,
                f"Interesse {interesse.numero} está agora em seu atendimento.",
                messages.SUCCESS,
            )
        except InteresseCompraServiceError as e:
            self.message_user(request, str(e), messages.ERROR)

        return redirect(
            reverse("vendedores:corretor_interessecompra_change", args=[object_id])
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
                f"Interesse {interesse.numero} convertido com sucesso! Uma ordem de compra foi criada.",
                messages.SUCCESS,
            )
        except InteresseCompraServiceError as e:
            self.message_user(request, str(e), messages.ERROR)

        return redirect(
            reverse("vendedores:corretor_interessecompra_change", args=[object_id])
        )

    @action(
        description="Descartar",
        url_path="descartar",
        permissions=["detail_descartar"],
    )
    def detail_descartar(self, request: HttpRequest, object_id: int) -> HttpResponse:
        """Descarta o interesse."""
        interesse = get_object_or_404(InteresseCompra, pk=object_id)
        form = DescarteInteresseForm(request.POST or None)

        if request.method == "POST" and form.is_valid():
            try:
                InteresseCompraService.descartar(
                    interesse, form.cleaned_data.get("motivo", "")
                )
                self.message_user(
                    request,
                    f"Interesse {interesse.numero} foi descartado.",
                    messages.WARNING,
                )
                return redirect(
                    reverse("vendedores:corretor_interessecompra_change", args=[object_id])
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
            "admin/corretor/interessecompra/action_descartar_vendedor.html",
            context,
        )


class OrdemCompraVendedorAdmin(TenantAwareAdminMixin, ModelAdmin):
    """
    Admin de ordens de compra para vendedores.

    Vendedores podem ver ordens de compra vinculadas a eles.
    """

    list_display = [
        "numero",
        "nome_cliente",
        "valor_total",
        "status",
        "corretor",
        "created",
    ]
    list_filter = ["status", "created"]
    search_fields = ["numero", "nome_cliente", "corretor__usuario__name"]
    readonly_fields = [
        "numero",
        "interesse",
        "nome_cliente",
        "telefone_cliente",
        "email_cliente",
        "valor_total",
        "observacoes",
        "corretor",
        "created",
        "modified",
    ]

    def get_queryset(self, request):
        """Filtra para mostrar apenas ordens do vendedor logado."""
        qs = super().get_queryset(request)

        # Superusuários veem tudo
        if request.user.is_superuser:
            return qs

        # Funcionários veem apenas suas ordens
        if hasattr(request.user, "funcionario"):
            funcionario = request.user.funcionario

            # Gerentes e admins veem todas as ordens da empresa
            if funcionario.is_gerente:
                return qs

            # Vendedores veem apenas ordens deles
            return qs.filter(corretor=funcionario)

        return qs.none()

    def has_add_permission(self, request):
        """Vendedores não podem criar ordens manualmente."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Vendedores não podem excluir ordens."""
        return False

    def has_change_permission(self, request, obj=None):
        """Vendedores não podem editar ordens."""
        return False


class VendedorAdminSite(UnfoldAdminSite):
    """
    Portal administrativo para vendedores.

    Funcionalidades:
    - Visualizar catálogo de produtos
    - Ver e atender interesses de compra atribuídos
    - Visualizar ordens de compra realizadas
    """

    site_header = "Portal do Vendedor"
    site_title = "Portal de Vendas"
    index_title = "Minhas Vendas"

    settings_name = "UNFOLD_VENDEDOR_ADMIN"

    def has_permission(self, request):
        """
        Verifica se o usuário tem permissão para acessar o portal de vendedores.

        Acesso permitido para:
        - Superusuários
        - Funcionários com papel VENDEDOR, GERENTE ou ADMIN
        """
        if not request.user.is_authenticated or not request.user.is_active:
            return False

        if request.user.is_superuser:
            return True

        # Funcionário precisa ter empresa e ser pelo menos vendedor
        if hasattr(request.user, "funcionario") and request.user.funcionario:
            funcionario = request.user.funcionario
            if funcionario.empresa is None:
                return False
            return funcionario.is_vendedor

        return False

    def _get_tenant_customization(self, tenant):
        """Retorna dicionário com customizações do tenant."""
        if not tenant:
            return {
                "site_header": "Portal do Vendedor",
                "site_title": "Portal de Vendas",
                "index_title": "Minhas Vendas",
                "admin_logo_url": None,
                "admin_favicon_url": None,
                "primary_color": "#10b981",  # Verde para vendedores
                "secondary_color": "#64748b",
                "accent_color": "#f59e0b",
                "sidebar_style": "dark",
                "welcome_message": "",
                "footer_text": "",
            }

        return {
            "site_header": f"Portal do Vendedor - {tenant.nome}",
            "site_title": f"Vendas - {tenant.nome}",
            "index_title": "Minhas Vendas",
            "admin_logo_url": tenant.admin_logo.url if tenant.admin_logo else None,
            "admin_favicon_url": tenant.admin_favicon.url if tenant.admin_favicon else None,
            "primary_color": "#10b981",  # Cor verde para diferenciar do gerente
            "secondary_color": tenant.secondary_color,
            "accent_color": tenant.accent_color,
            "sidebar_style": tenant.sidebar_style,
            "welcome_message": tenant.welcome_message,
            "footer_text": tenant.footer_text or f"© {tenant.nome}",
        }

    def each_context(self, request):
        context = super().each_context(request)
        context["site_url"] = "/vendedores"

        # Adiciona informações do tenant ao contexto
        tenant = getattr(request, "tenant", None)
        context["tenant"] = tenant
        context["tenant_name"] = tenant.nome if tenant else None

        # Customizações baseadas no tenant
        customization = self._get_tenant_customization(tenant)

        # Atualiza atributos do site dinamicamente
        self.site_header = customization["site_header"]
        self.site_title = customization["site_title"]

        # Adiciona customizações ao contexto
        context["tenant_customization"] = customization
        context["admin_logo_url"] = customization["admin_logo_url"]
        context["admin_favicon_url"] = customization["admin_favicon_url"]
        context["theme_colors"] = {
            "primary": customization["primary_color"],
            "secondary": customization["secondary_color"],
            "accent": customization["accent_color"],
        }
        context["sidebar_style"] = customization["sidebar_style"]
        context["welcome_message"] = customization["welcome_message"]
        context["footer_text"] = customization["footer_text"]

        # Adiciona informações do vendedor logado
        if hasattr(request.user, "funcionario"):
            context["vendedor"] = request.user.funcionario

        # Lista empresas disponíveis para superusuários
        if request.user.is_superuser and not tenant:
            context["available_empresas"] = Empresa.objects.all().order_by("nome")

        # Mostra aviso se não houver tenant selecionado
        if not tenant and request.user.is_superuser:
            if not request.session.get("_vendedor_tenant_warning_shown"):
                messages.warning(
                    request,
                    "Nenhuma empresa selecionada. Use ?tenant=SLUG para selecionar."
                )
                request.session["_vendedor_tenant_warning_shown"] = True

        if tenant:
            request.session.pop("_vendedor_tenant_warning_shown", None)

        return context

    def index(self, request, extra_context=None):
        """Sobrescreve index para adicionar contexto extra."""
        extra_context = extra_context or {}
        tenant = getattr(request, "tenant", None)
        customization = self._get_tenant_customization(tenant)

        extra_context["index_title"] = customization["index_title"]
        self.index_title = customization["index_title"]

        if customization["welcome_message"]:
            extra_context["welcome_message"] = customization["welcome_message"]

        return super().index(request, extra_context)


# Instância do site
vendedor_site = VendedorAdminSite(name="vendedores")

# Registra modelos com acesso limitado
vendedor_site.register(Produto, ProdutoVendedorAdmin)
vendedor_site.register(Categoria, CategoriaVendedorAdmin)
vendedor_site.register(InteresseCompra, InteresseCompraVendedorAdmin)
vendedor_site.register(OrdemCompra, OrdemCompraVendedorAdmin)
vendedor_site.register(Comissao, ComissaoVendedorAdminReadOnly)
