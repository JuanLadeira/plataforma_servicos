from django.contrib import admin

from plataforma_de_servicos.produto.models.produto_model import Produto
from plataforma_de_servicos.core.admin.sites import gerente_site
from unfold.admin import ModelAdmin

# Instância global do site dos gerentes

@admin.register(Produto, site=gerente_site)
class ProdutoGerenteAdmin(ModelAdmin):
    list_display = ['produto', 'preco']
    search_fields = ['produto',]

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
