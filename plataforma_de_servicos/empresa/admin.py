from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import Empresa
from .models import TipoIsolamento
from .services import SchemaManager
from .services import SchemaManagerError


@admin.register(Empresa)
class EmpresaAdmin(ModelAdmin):
    """Admin para gerenciar Empresas (apenas no admin principal)."""

    list_display = [
        "nome",
        "slug",
        "email",
        "get_tipo_isolamento_badge",
        "get_schema_status",
        "admin_url",
        "vendedor_url",
        "get_color_preview",
    ]
    list_filter = ["tipo_isolamento", "schema_criado", "sidebar_style"]
    search_fields = ["nome", "slug", "email"]
    prepopulated_fields = {"slug": ("nome",)}
    readonly_fields = [
        "get_gerente_full_url",
        "get_vendedor_full_url",
        "get_color_preview_large",
        "get_schema_status_detail",
        "schema_criado",
        "schema_criado_em",
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
                "Use URLs unicas para maior seguranca (ex: 'painel-2024', 'minha-equipe')."
            ),
        }),
        ("Isolamento de Dados", {
            "fields": (
                "tipo_isolamento",
                "schema_name",
                "get_schema_status_detail",
            ),
            "description": (
                "Configure como os dados desta empresa sao isolados. "
                "Compartilhado: dados filtrados por empresa na mesma tabela (padrao). "
                "Dedicado: schema PostgreSQL exclusivo para maior isolamento."
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
            "classes": ["collapse"],
        }),
        ("Cores do Tema", {
            "fields": (
                "primary_color",
                "secondary_color",
                "accent_color",
                "sidebar_style",
                "get_color_preview_large",
            ),
            "description": "Configure as cores do tema do painel. Use codigos hexadecimais (ex: #0ea5e9).",
            "classes": ["collapse"],
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

    @admin.display(description="Isolamento")
    def get_tipo_isolamento_badge(self, obj):
        """Badge showing isolation type and status."""
        if obj.tipo_isolamento == TipoIsolamento.DEDICADO:
            if obj.schema_criado:
                color = "#10b981"  # green
                label = "Dedicado"
            else:
                color = "#f59e0b"  # amber
                label = "Dedicado (Pendente)"
        else:
            color = "#6b7280"  # gray
            label = "Compartilhado"

        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, label
        )

    @admin.display(description="Schema")
    def get_schema_status(self, obj):
        """Schema name or status in list view."""
        if obj.tipo_isolamento != TipoIsolamento.DEDICADO:
            return "-"
        if obj.schema_criado:
            return format_html(
                '<code style="color: #10b981;">{}</code>',
                obj.schema_name
            )
        return format_html('<span style="color: #f59e0b;">Pendente</span>')

    @admin.display(description="Status do Schema")
    def get_schema_status_detail(self, obj):
        """Detailed schema status for form view."""
        if obj.tipo_isolamento != TipoIsolamento.DEDICADO:
            return format_html(
                '<span style="color: #6b7280;">N/A - Usando banco compartilhado</span>'
            )

        if obj.schema_criado:
            criado_em = (
                obj.schema_criado_em.strftime("%d/%m/%Y %H:%M")
                if obj.schema_criado_em else "-"
            )
            return format_html(
                '<span style="color: #10b981;">&#10003; Provisionado</span><br>'
                '<strong>Schema:</strong> <code>{}</code><br>'
                '<strong>Criado em:</strong> {}',
                obj.schema_name,
                criado_em,
            )

        return format_html(
            '<span style="color: #f59e0b;">&#8987; Aguardando provisionamento</span><br>'
            '<small>Salve para criar o schema automaticamente.</small>'
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
                '<span style="background:{};width:16px;height:16px;border-radius:2px;display:inline-block;" title="Primaria"></span>'
                '<span style="background:{};width:16px;height:16px;border-radius:2px;display:inline-block;" title="Secundaria"></span>'
                '<span style="background:{};width:16px;height:16px;border-radius:2px;display:inline-block;" title="Destaque"></span>'
                '</span>',
                obj.primary_color,
                obj.secondary_color,
                obj.accent_color,
            )
        return "-"

    @admin.display(description="Preview das Cores")
    def get_color_preview_large(self, obj):
        """Mostra preview detalhado das cores no formulario."""
        if obj.pk:
            return format_html(
                '<div style="display:flex;gap:16px;align-items:center;">'
                '<div style="text-align:center;">'
                '<div style="background:{};width:60px;height:40px;border-radius:4px;margin-bottom:4px;"></div>'
                '<small>Primaria</small>'
                '</div>'
                '<div style="text-align:center;">'
                '<div style="background:{};width:60px;height:40px;border-radius:4px;margin-bottom:4px;"></div>'
                '<small>Secundaria</small>'
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

    def save_model(self, request, obj, form, change):
        """Save model and create schema if needed."""
        # Save first
        super().save_model(request, obj, form, change)

        # If changed to DEDICADO and schema doesn't exist, create it
        if (
            obj.tipo_isolamento == TipoIsolamento.DEDICADO
            and not obj.schema_criado
        ):
            try:
                schema_name = SchemaManager.create_schema(obj)
                messages.success(
                    request,
                    f"Schema '{schema_name}' criado e migracoes aplicadas com sucesso!"
                )
            except SchemaManagerError as e:
                messages.error(request, f"Erro ao criar schema: {e}")
