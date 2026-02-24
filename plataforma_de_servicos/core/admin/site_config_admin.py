from django.contrib import admin
from unfold.admin import ModelAdmin

from plataforma_de_servicos.core.admin.mixins import TenantAwareAdminMixin
from plataforma_de_servicos.core.models import SiteConfig


@admin.register(SiteConfig)
class SiteConfigAdmin(ModelAdmin):
    """Admin para configurações do site (singleton global)."""

    list_display = ("empresa", "site_name", "theme", "hero_title", "modified")
    readonly_fields = ("created", "modified")

    fieldsets = [
        (
            "Empresa",
            {
                "fields": ["empresa"],
                "description": "Empresa dona desta configuração.",
            },
        ),
        (
            "Identidade do Site",
            {
                "fields": ["site_name", "logo"],
                "description": "Nome e logo exibidos no navbar do site.",
            },
        ),
        (
            "Tema e Cores",
            {
                "fields": ["theme"],
                "description": "Escolha um tema de cores para o site. O tema define cores do navbar, fundo, textos e botões.",
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

    def has_delete_permission(self, request, obj=None):
        # Não permite deletar a configuração
        return False


class SiteConfigGerenteAdmin(TenantAwareAdminMixin, ModelAdmin):
    """Admin para configurações do site no painel de gerentes (filtrado por tenant)."""

    list_display = ("site_name", "theme", "hero_title", "modified")
    readonly_fields = ("created", "modified")

    fieldsets = [
        (
            "Identidade do Site",
            {
                "fields": ["site_name", "logo"],
                "description": "Nome e logo exibidos no navbar do site.",
            },
        ),
        (
            "Tema e Cores",
            {
                "fields": ["theme"],
                "description": "Escolha um tema de cores para personalizar seu site. Cada tema possui uma paleta de cores harmoniosa.",
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
        # Permite adicionar apenas se não existir configuração para a empresa
        tenant = getattr(request, "tenant", None)
        if tenant:
            return not SiteConfig.objects.filter(empresa=tenant).exists()
        return False

    def has_delete_permission(self, request, obj=None):
        return False
