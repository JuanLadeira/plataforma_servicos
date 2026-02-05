from unfold.admin import ModelAdmin
from unfold.admin import TabularInline

from plataforma_de_servicos.core.admin.mixins import TenantAwareAdminMixin
from plataforma_de_servicos.corretor.models import ItemInteresse


class CorretorGerenteAdmin(TenantAwareAdminMixin, ModelAdmin):
    list_display = ["nome", "email", "telefone", "ativo", "created"]
    list_filter = ["ativo", "created"]
    search_fields = ["nome", "email", "telefone"]
    readonly_fields = ["created", "modified"]
    fieldsets = [
        (
            None,
            {
                "fields": ["nome", "email", "telefone", "ativo"],
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


class ItemInteresseGerenteInline(TabularInline):
    model = ItemInteresse
    extra = 0
    readonly_fields = ["produto_nome", "variacao_info", "quantidade", "preco_unitario"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class InteresseCompraGerenteAdmin(TenantAwareAdminMixin, ModelAdmin):
    list_display = [
        "id",
        "nome_cliente",
        "email_cliente",
        "telefone_cliente",
        "valor_total",
        "status",
        "corretor",
        "created",
    ]
    list_display_links = ["id", "nome_cliente"]
    list_filter = ["status", "corretor", "created"]
    search_fields = ["nome_cliente", "email_cliente", "telefone_cliente"]
    autocomplete_fields = ["corretor"]
    readonly_fields = [
        "nome_cliente",
        "email_cliente",
        "telefone_cliente",
        "mensagem",
        "valor_total",
        "created",
        "modified",
    ]
    inlines = [ItemInteresseGerenteInline]
    fieldsets = [
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
