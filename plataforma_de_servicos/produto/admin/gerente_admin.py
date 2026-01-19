from django.contrib import admin
from django.contrib.postgres.fields import ArrayField
from django.db import models
from unfold.admin import ModelAdmin
from unfold.admin import TabularInline
from unfold.contrib.forms.widgets import ArrayWidget
from unfold.contrib.forms.widgets import WysiwygWidget

from plataforma_de_servicos.produto.models import Atributo
from plataforma_de_servicos.produto.models import Image
from plataforma_de_servicos.produto.models import Produto
from plataforma_de_servicos.produto.models import ValorAtributo
from plataforma_de_servicos.produto.models import VariacaoProduto


class ImageInline(TabularInline):
    model = Image
    extra = 0
    verbose_name = "Imagem"
    verbose_name_plural = "Imagens"
    show_change_link = True

    readonly_fields = ["order"]


class VariacaoProdutoInline(TabularInline):
    model = VariacaoProduto
    extra = 1
    autocomplete_fields = ("valores",)
    readonly_fields = ("preco_final_calculado",)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "valores":
            kwargs["queryset"] = ValorAtributo.objects.select_related(
                "atributo",
            ).order_by("atributo__nome", "valor")
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    @admin.display(description="Preço Final")
    def preco_final_calculado(self, obj):
        if obj.pk:
            preco_final = obj.calcular_preco_final()
            return f"R$ {preco_final:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return "-"


class ProdutoGerenteAdmin(ModelAdmin):
    list_display = ["produto", "categoria", "count_variations"]
    list_display_links = ["produto"]
    list_per_page = 30
    list_select_related = ["categoria"]
    list_order_by = ["produto"]
    list_search = ["produto", "categoria__categoria"]
    search_fields = ["produto"]
    fieldsets = [
        (
            "Produto",
            {
                "fields": [
                    "produto",
                    "importado",
                    "ncm",
                    "estoque_minimo",
                    "data",
                ],
            },
        ),
        (
            "Categoria",
            {
                "fields": [
                    "categoria",
                ],
            },
        ),
    ]
    inlines = [ImageInline, VariacaoProdutoInline]
    readonly_fields = ["data"]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related("variacoes")
        return queryset

    @admin.display(description="Variações")
    def count_variations(self, obj):
        return obj.variacoes.count()

    # Manter outras configurações do ModelAdmin
    compressed_fields = True
    warn_unsaved_form = True
    list_filter_submit = True
    list_fullwidth = True
    list_horizontal_scrollbar_top = True
    list_disable_select_all = True
    actions_list = []
    actions_row = []
    actions_detail = []
    actions_submit_line = []
    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        },
        ArrayField: {
            "widget": ArrayWidget,
        },
    }


class ProdutoInline(TabularInline):
    model = Produto
    extra = 0
    verbose_name = "Produto"
    verbose_name_plural = "Produtos"
    show_change_link = True
    fieldsets = [
        (
            "Produto",
            {
                "fields": [
                    "produto",
                    "importado",
                    "ncm",
                    "estoque_minimo",
                    "data",
                ],
            },
        ),
        (
            "Categoria",
            {
                "fields": [
                    "categoria",
                ],
            },
        ),
    ]
    readonly_fields = ["produto", "data", "ncm", "importado"]


class CategoriaGerenteAdmin(ModelAdmin):
    list_display = ["categoria"]
    list_order_by = ["categoria"]
    list_order_by_desc = ["-categoria"]

    list_search = ["categoria"]
    list_search_fields = ["categoria"]

    search_fields = ["categoria"]

    inlines = [ProdutoInline]

    compressed_fields = True
    warn_unsaved_form = True

    list_filter_submit = True
    list_fullwidth = True

    list_horizontal_scrollbar_top = True
    list_disable_select_all = True

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()


class ValorAtributoGerenteInline(TabularInline):
    model = ValorAtributo
    extra = 1


class AtributoGerenteAdmin(ModelAdmin):
    list_display = ["nome"]
    search_fields = ["nome"]
    list_order_by = ["nome"]
    inlines = [ValorAtributoGerenteInline]
    compressed_fields = True
    warn_unsaved_form = True


class ValorAtributoGerenteAdmin(ModelAdmin):
    list_display = ["atributo", "valor", "preco_adicional", "percentual_adicional"]
    list_filter = ["atributo"]
    search_fields = ["valor", "atributo__nome"]
    autocomplete_fields = ["atributo"]
    list_select_related = ["atributo"]
    list_order_by = ["atributo__nome", "valor"]
    list_editable = ["preco_adicional", "percentual_adicional"]
    compressed_fields = True
    warn_unsaved_form = True
    fieldsets = [
        ("Atributo", {
            "fields": ["atributo", "valor"]
        }),
        ("Modificadores de Preço", {
            "fields": ["preco_adicional", "percentual_adicional"],
            "description": "Configure modificações no preço base quando este atributo for selecionado"
        })
    ]
