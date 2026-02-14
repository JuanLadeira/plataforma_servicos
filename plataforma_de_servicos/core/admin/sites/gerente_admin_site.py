from django.contrib import admin
from django.contrib import messages
from unfold.admin import ModelAdmin
from unfold.sites import UnfoldAdminSite

from plataforma_de_servicos.core.admin.mixins import TenantAwareAdminMixin
from plataforma_de_servicos.core.admin.site_config_admin import SiteConfigGerenteAdmin
from plataforma_de_servicos.core.models import SiteConfig
from plataforma_de_servicos.corretor.admin.gerente_admin import (
    InteresseCompraGerenteAdmin,
)
from plataforma_de_servicos.corretor.models import InteresseCompra
from plataforma_de_servicos.empresa.models import Empresa
from plataforma_de_servicos.users.models import Funcionario
from plataforma_de_servicos.users.models import User
from plataforma_de_servicos.estoque.admin.gerente_admin import EstoqueEntradaAdmin
from plataforma_de_servicos.estoque.admin.gerente_admin import EstoqueSaidaAdmin
from plataforma_de_servicos.estoque.admin.gerente_admin import TransferenciaAdmin
from plataforma_de_servicos.estoque.models.proxys.estoque_entrada import EstoqueEntrada
from plataforma_de_servicos.estoque.models.proxys.estoque_saida import EstoqueSaida
from plataforma_de_servicos.estoque.models.proxys.transferencia import Transferencia
from plataforma_de_servicos.inventario.admin.gerente_admin import InventarioGerenteAdmin
from plataforma_de_servicos.inventario.models import Inventario
from plataforma_de_servicos.produto.admin.gerente_admin import AtributoGerenteAdmin
from plataforma_de_servicos.produto.admin.gerente_admin import CategoriaGerenteAdmin
from plataforma_de_servicos.produto.admin.gerente_admin import ProdutoGerenteAdmin
from plataforma_de_servicos.produto.admin.gerente_admin import ValorAtributoGerenteAdmin
from plataforma_de_servicos.produto.admin.gerente_admin import VariacaoProdutoGerenteAdmin
from plataforma_de_servicos.produto.models.atributos import Atributo
from plataforma_de_servicos.produto.models.atributos import ValorAtributo
from plataforma_de_servicos.produto.models.atributos import VariacaoProduto
from plataforma_de_servicos.produto.models.categoria_model import Categoria
from plataforma_de_servicos.produto.models.produto_model import Produto
from plataforma_de_servicos.vendas.admin import OrdemCompraGerenteAdmin
from plataforma_de_servicos.vendas.models import OrdemCompra


class UserGerenteAdmin(TenantAwareAdminMixin, ModelAdmin):
    """Admin para User no site de gerentes."""

    list_display = ["email", "name", "user_type", "is_active", "date_joined"]
    list_filter = ["is_active", "user_type", "date_joined"]
    search_fields = ["email", "name"]
    readonly_fields = ["date_joined", "last_login"]
    fieldsets = [
        (
            "Dados de Acesso",
            {
                "fields": ["email", "password"],
            },
        ),
        (
            "Informações Pessoais",
            {
                "fields": ["name"],
            },
        ),
        (
            "Tipo e Status",
            {
                "fields": ["user_type", "is_active"],
            },
        ),
        (
            "Datas",
            {
                "fields": ["date_joined", "last_login"],
                "classes": ["collapse"],
            },
        ),
    ]

    def save_model(self, request, obj, form, change):
        """Se senha foi alterada, faz o hash. Auto-preenche empresa."""
        if "password" in form.changed_data:
            obj.set_password(form.cleaned_data["password"])
        # Auto-preenche empresa do tenant
        if not change and not obj.empresa_id:
            tenant = getattr(request, "tenant", None)
            if tenant:
                obj.empresa = tenant
        super().save_model(request, obj, form, change)


class FuncionarioGerenteAdmin(TenantAwareAdminMixin, ModelAdmin):
    """Admin para Funcionario no site de gerentes."""

    list_display = ["usuario", "cargo", "telefone", "is_corretor", "is_signatario", "ativo"]
    list_filter = ["is_corretor", "is_signatario", "ativo"]
    search_fields = ["usuario__name", "usuario__email", "cargo", "cpf", "telefone"]
    autocomplete_fields = ["usuario"]
    fieldsets = [
        (
            "Usuário",
            {
                "fields": ["usuario"],
            },
        ),
        (
            "Dados do Funcionário",
            {
                "fields": ["cargo", "endereco", "cpf", "telefone"],
            },
        ),
        (
            "Permissões",
            {
                "fields": ["is_corretor", "is_signatario", "ativo"],
            },
        ),
    ]


class GerenteAdminSite(UnfoldAdminSite):
    # Valores padrão (serão sobrescritos por tenant)
    site_header = "Portal dos Gerentes"
    site_title = "Gestão de Produtos e Serviços"
    index_title = "Administração dos Gerentes"

    settings_name = "UNFOLD_GERENTE_ADMIN"

    def has_permission(self, request):
        """
        Verifica se o usuário tem permissão para acessar o site.
        - Superusuários sempre têm acesso
        - Funcionários precisam ter empresa associada
        """
        if not request.user.is_authenticated or not request.user.is_active:
            return False

        if request.user.is_superuser:
            return True

        # Funcionário precisa ter empresa associada
        if hasattr(request.user, "funcionario") and request.user.funcionario:
            return request.user.funcionario.empresa is not None

        return False

    def _get_tenant_customization(self, tenant):
        """Retorna dicionário com customizações do tenant."""
        if not tenant:
            return {
                "site_header": "Portal dos Gerentes",
                "site_title": "Gestão de Produtos e Serviços",
                "index_title": "Administração dos Gerentes",
                "admin_logo_url": None,
                "admin_favicon_url": None,
                "primary_color": "#0ea5e9",
                "secondary_color": "#64748b",
                "accent_color": "#f59e0b",
                "sidebar_style": "dark",
                "welcome_message": "",
                "footer_text": "",
            }

        return {
            "site_header": tenant.get_admin_title(),
            "site_title": tenant.admin_subtitle or f"Gestão - {tenant.nome}",
            "index_title": f"Bem-vindo ao {tenant.get_admin_title()}",
            "admin_logo_url": tenant.admin_logo.url if tenant.admin_logo else None,
            "admin_favicon_url": tenant.admin_favicon.url if tenant.admin_favicon else None,
            "primary_color": tenant.primary_color,
            "secondary_color": tenant.secondary_color,
            "accent_color": tenant.accent_color,
            "sidebar_style": tenant.sidebar_style,
            "welcome_message": tenant.welcome_message,
            "footer_text": tenant.footer_text or f"© {tenant.nome}",
        }

    def each_context(self, request):
        context = super().each_context(request)
        context["site_url"] = "/gerentes"

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

        # Lista empresas disponíveis para superusuários (para seleção)
        if request.user.is_superuser and not tenant:
            context["available_empresas"] = Empresa.objects.all().order_by("nome")

        # Mostra aviso se não houver tenant selecionado
        if not tenant and request.user.is_superuser:
            # Verifica se já não mostrou a mensagem nesta sessão
            if not request.session.get("_tenant_warning_shown"):
                messages.warning(
                    request,
                    "Nenhuma empresa selecionada. Os dados não serão filtrados. "
                    "Use ?tenant=SLUG para selecionar uma empresa. "
                    "Ex: /gerentes/?tenant=empresa-teste"
                )
                request.session["_tenant_warning_shown"] = True

        # Se tenant foi setado, limpa o aviso
        if tenant:
            request.session.pop("_tenant_warning_shown", None)

        return context

    def index(self, request, extra_context=None):
        """Sobrescreve index para adicionar contexto extra."""
        extra_context = extra_context or {}
        tenant = getattr(request, "tenant", None)
        customization = self._get_tenant_customization(tenant)

        extra_context["index_title"] = customization["index_title"]
        self.index_title = customization["index_title"]

        # Adiciona mensagem de boas-vindas se existir
        if customization["welcome_message"]:
            extra_context["welcome_message"] = customization["welcome_message"]

        return super().index(request, extra_context)


gerente_site = GerenteAdminSite(name="gerentes")

gerente_site.register(Produto, ProdutoGerenteAdmin)
gerente_site.register(Categoria, CategoriaGerenteAdmin)
gerente_site.register(Atributo, AtributoGerenteAdmin)
gerente_site.register(ValorAtributo, ValorAtributoGerenteAdmin)
gerente_site.register(VariacaoProduto, VariacaoProdutoGerenteAdmin)
gerente_site.register(EstoqueEntrada, EstoqueEntradaAdmin)
gerente_site.register(EstoqueSaida, EstoqueSaidaAdmin)
gerente_site.register(Transferencia, TransferenciaAdmin)
gerente_site.register(Inventario, InventarioGerenteAdmin)
gerente_site.register(InteresseCompra, InteresseCompraGerenteAdmin)
gerente_site.register(OrdemCompra, OrdemCompraGerenteAdmin)
gerente_site.register(User, UserGerenteAdmin)
gerente_site.register(Funcionario, FuncionarioGerenteAdmin)
gerente_site.register(SiteConfig, SiteConfigGerenteAdmin)
