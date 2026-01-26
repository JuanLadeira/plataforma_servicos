from django.contrib import admin
from unfold.admin import ModelAdmin

from plataforma_de_servicos.core.models import SiteConfig


@admin.register(SiteConfig)
class SiteConfigAdmin(ModelAdmin):
    """Admin para configurações do site (singleton)."""

    list_display = ("site_name", "hero_title", "modified")
    readonly_fields = ("created", "modified")

    fieldsets = [
        (
            "Identidade do Site",
            {
                "fields": ["site_name"],
                "description": "Nome exibido no navbar do site.",
            },
        ),
        (
            "Banner Principal (Hero)",
            {
                "fields": [
                    "hero_title",
                    "hero_description",
                    "hero_button_text",
                ],
                "description": "Textos exibidos na seção principal da home page.",
            },
        ),
        (
            "Imagem do Banner",
            {
                "fields": ["hero_image", "hero_image_url"],
                "description": "Upload de imagem tem prioridade sobre URL. Se nenhum upload, usa a URL.",
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

    def has_add_permission(self, request):
        # Permite adicionar apenas se não existir nenhuma instância
        return not SiteConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Não permite deletar a configuração
        return False


class SiteConfigGerenteAdmin(ModelAdmin):
    """Admin para configurações do site no painel de gerentes."""

    list_display = ("site_name", "hero_title", "modified")
    readonly_fields = ("created", "modified")

    fieldsets = [
        (
            "Identidade do Site",
            {
                "fields": ["site_name"],
                "description": "Nome exibido no navbar do site.",
            },
        ),
        (
            "Banner Principal (Hero)",
            {
                "fields": [
                    "hero_title",
                    "hero_description",
                    "hero_button_text",
                ],
                "description": "Textos exibidos na seção principal da home page.",
            },
        ),
        (
            "Imagem do Banner",
            {
                "fields": ["hero_image", "hero_image_url"],
                "description": "Upload de imagem tem prioridade sobre URL. Se nenhum upload, usa a URL.",
            },
        ),
    ]

    def has_add_permission(self, request):
        return not SiteConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
