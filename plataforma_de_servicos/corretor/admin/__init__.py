from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.admin import TabularInline

from plataforma_de_servicos.corretor.models import InteresseCompra
from plataforma_de_servicos.corretor.models import ItemInteresse


class ItemInteresseInline(TabularInline):
    model = ItemInteresse
    extra = 0
    readonly_fields = ["produto_nome", "variacao_info", "quantidade", "preco_unitario"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(InteresseCompra)
class InteresseCompraAdmin(ModelAdmin):
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
    inlines = [ItemInteresseInline]
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
