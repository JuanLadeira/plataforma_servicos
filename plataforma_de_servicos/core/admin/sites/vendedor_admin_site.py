"""
Portal administrativo para vendedores.

Este portal oferece funcionalidades limitadas para vendedores,
incluindo visualização de interesses, ordens de compra (suas) e catálogo.
"""
from django.contrib import messages
from unfold.admin import ModelAdmin
from unfold.sites import UnfoldAdminSite

from plataforma_de_servicos.core.admin.mixins import TenantAwareAdminMixin
from plataforma_de_servicos.corretor.models import InteresseCompra
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


class InteresseCompraVendedorAdmin(TenantAwareAdminMixin, ModelAdmin):
    """
    Admin de interesses de compra para vendedores.

    Vendedores podem ver e atender interesses atribuídos a eles.
    """

    list_display = [
        "numero",
        "nome_cliente",
        "telefone_cliente",
        "status",
        "corretor",
        "created",
    ]
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
        "created",
    ]

    def get_queryset(self, request):
        """Filtra para mostrar apenas interesses do vendedor logado."""
        qs = super().get_queryset(request)

        # Superusuários veem tudo
        if request.user.is_superuser:
            return qs

        # Funcionários veem apenas seus interesses
        if hasattr(request.user, "funcionario"):
            funcionario = request.user.funcionario

            # Gerentes e admins veem todos os interesses da empresa
            if funcionario.is_gerente:
                return qs

            # Vendedores veem apenas interesses atribuídos a eles
            return qs.filter(corretor=funcionario)

        return qs.none()

    def has_add_permission(self, request):
        """Vendedores não podem criar interesses manualmente."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Vendedores não podem excluir interesses."""
        return False


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
