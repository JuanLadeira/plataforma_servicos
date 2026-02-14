from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import Empresa


@admin.register(Empresa)
class EmpresaAdmin(ModelAdmin):
    """Admin para gerenciar Empresas (apenas no admin principal)."""

    list_display = [
        "nome",
        "slug",
        "email",
        "admin_url",
        "vendedor_url",
        "get_color_preview",
    ]
    list_filter = ["sidebar_style"]
    search_fields = ["nome", "slug", "email"]
    prepopulated_fields = {"slug": ("nome",)}
    readonly_fields = [
        "get_gerente_full_url",
        "get_vendedor_full_url",
        "get_color_preview_large",
    ]

    fieldsets = (
        ("Dados da Empresa", {
            "fields": ("nome", "slug", "email", "imo", "foto"),
        }),
        ("URLs dos Portais Administrativos", {
            "fields": (
                "admin_url",
                "get_gerente_full_url",
                "vendedor_url",
                "get_vendedor_full_url",
            ),
            "description": (
                "Configure os endpoints dos portais administrativos. "
                "Use URLs únicas para maior segurança (ex: 'painel-2024', 'minha-equipe')."
            ),
        }),
        ("Identidade Visual do Admin", {
            "fields": (
                "admin_title",
                "admin_subtitle",
                "admin_logo",
                "admin_favicon",
            ),
            "description": "Personalize a identidade visual do painel administrativo.",
        }),
        ("Cores do Tema", {
            "fields": (
                "primary_color",
                "secondary_color",
                "accent_color",
                "sidebar_style",
                "get_color_preview_large",
            ),
            "description": "Configure as cores do tema do painel. Use códigos hexadecimais (ex: #0ea5e9).",
        }),
        ("Textos Personalizados", {
            "fields": (
                "welcome_message",
                "footer_text",
            ),
            "description": "Personalize os textos exibidos no painel administrativo.",
            "classes": ["collapse"],
        }),
    )

    @admin.display(description="URL do Portal de Gerentes")
    def get_gerente_full_url(self, obj):
        if obj.pk:
            return format_html(
                '<code>https://{}.seudominio.com{}</code>',
                obj.slug,
                obj.get_admin_url(),
            )
        return "-"

    @admin.display(description="URL do Portal de Vendedores")
    def get_vendedor_full_url(self, obj):
        if obj.pk:
            return format_html(
                '<code>https://{}.seudominio.com{}</code>',
                obj.slug,
                obj.get_vendedor_url(),
            )
        return "-"

    @admin.display(description="Cores")
    def get_color_preview(self, obj):
        """Mostra preview das cores na listagem."""
        if obj.pk:
            return format_html(
                '<span style="display:inline-flex;gap:2px;">'
                '<span style="background:{};width:16px;height:16px;border-radius:2px;display:inline-block;" title="Primária"></span>'
                '<span style="background:{};width:16px;height:16px;border-radius:2px;display:inline-block;" title="Secundária"></span>'
                '<span style="background:{};width:16px;height:16px;border-radius:2px;display:inline-block;" title="Destaque"></span>'
                '</span>',
                obj.primary_color,
                obj.secondary_color,
                obj.accent_color,
            )
        return "-"

    @admin.display(description="Preview das Cores")
    def get_color_preview_large(self, obj):
        """Mostra preview detalhado das cores no formulário."""
        if obj.pk:
            return format_html(
                '<div style="display:flex;gap:16px;align-items:center;">'
                '<div style="text-align:center;">'
                '<div style="background:{};width:60px;height:40px;border-radius:4px;margin-bottom:4px;"></div>'
                '<small>Primária</small>'
                '</div>'
                '<div style="text-align:center;">'
                '<div style="background:{};width:60px;height:40px;border-radius:4px;margin-bottom:4px;"></div>'
                '<small>Secundária</small>'
                '</div>'
                '<div style="text-align:center;">'
                '<div style="background:{};width:60px;height:40px;border-radius:4px;margin-bottom:4px;"></div>'
                '<small>Destaque</small>'
                '</div>'
                '</div>',
                obj.primary_color,
                obj.secondary_color,
                obj.accent_color,
            )
        return "-"
