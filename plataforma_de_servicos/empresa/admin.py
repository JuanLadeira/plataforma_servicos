from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Empresa


@admin.register(Empresa)
class EmpresaAdmin(ModelAdmin):
    """Admin para gerenciar Empresas (apenas no admin principal)."""

    list_display = ["nome", "slug", "email", "admin_url", "get_admin_full_url"]
    list_filter = ["admin_url"]
    search_fields = ["nome", "slug", "email"]
    prepopulated_fields = {"slug": ("nome",)}
    readonly_fields = ["get_admin_full_url"]

    fieldsets = (
        (None, {
            "fields": ("nome", "slug", "email", "imo", "foto"),
        }),
        ("Configurações do Admin", {
            "fields": ("admin_url", "get_admin_full_url"),
            "description": "Configure o endpoint do painel administrativo desta empresa.",
        }),
    )

    @admin.display(description="URL Completa do Admin")
    def get_admin_full_url(self, obj):
        if obj.pk:
            return f"https://{obj.slug}.seudominio.com{obj.get_admin_url()}"
        return "-"
