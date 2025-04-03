from django.contrib import admin
from django.db import models
from django.contrib.postgres.fields import ArrayField
from plataforma_de_servicos.produto.models.produto_model import Produto
from plataforma_de_servicos.produto.models.categoria_model import Categoria
from plataforma_de_servicos.core.admin.sites import gerente_site
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.forms.widgets import ArrayWidget, WysiwygWidget

@admin.register(Produto, site=gerente_site)
class ProdutoGerenteAdmin(ModelAdmin):
    list_display = ['produto', 'preco', "estoque", "estoque_minimo", "categoria"]
    list_display_links = ['produto',]
    list_editable = ['preco', "estoque_minimo", "categoria"]
    list_per_page = 30
    list_select_related = ['categoria']
    list_order_by = ['produto',]
    list_order_by_desc = ['-produto',]
    list_search = ['produto', 'categoria__categoria']
    list_search_fields = ['produto', 'categoria__categoria']
    search_fields = ['produto',]
    fieldsets = [
        (
            "Produto",
            {
                "fields": [
                    "produto",
                    "importado",
                    "ncm",
                    "preco",
                    "estoque",
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
    readonly_fields = ["estoque", "data"]

    compressed_fields = True
    warn_unsaved_form = True

    list_filter_submit = True
    list_fullwidth = True

    list_horizontal_scrollbar_top = True
    list_disable_select_all = True

    actions_list = []  # Displayed above the results list
    actions_row = []  # Displayed in a table row in results list
    actions_detail = []  # Displayed at the top of for in object detail
    actions_submit_line = []  # Displayed near save in object detail


    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
    
    def has_module_permission(self, request):
        return self.admin_site.has_permission(request)
    
    def has_add_permission(self, request):
        return self.admin_site.has_permission(request)
        
    def has_change_permission(self, request, obj=None):
        return self.admin_site.has_permission(request)
        
    def has_delete_permission(self, request, obj=None):
        return self.admin_site.has_permission(request)
        
    def has_view_permission(self, request, obj=None):
        return self.admin_site.has_permission(request)

    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        },
        ArrayField: {
            "widget": ArrayWidget,
        }
    }
    


class ProdutoInline(TabularInline):
    model = Produto
    extra = 0
    verbose_name = "Produto"
    verbose_name_plural = "Produtos"
    show_change_link = True


@admin.register(Categoria, site=gerente_site)
class CategoriaGerenteAdmin(ModelAdmin):
    list_display = ["categoria"]
    list_order_by = ["categoria",]
    list_order_by_desc = ['-categoria',]

    list_search = ["categoria", ]
    list_search_fields = ["categoria",]

    search_fields = ["categoria",]

    inlines = [ProdutoInline]


    compressed_fields = True
    warn_unsaved_form = True

    list_filter_submit = True
    list_fullwidth = True

    list_horizontal_scrollbar_top = True
    list_disable_select_all = True


    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
    
    def has_module_permission(self, request):
        return self.admin_site.has_permission(request)
    
    def has_add_permission(self, request):
        return self.admin_site.has_permission(request)
        
    def has_change_permission(self, request, obj=None):
        return self.admin_site.has_permission(request)
        
    def has_delete_permission(self, request, obj=None):
        return self.admin_site.has_permission(request)
        
    def has_view_permission(self, request, obj=None):
        return self.admin_site.has_permission(request)
