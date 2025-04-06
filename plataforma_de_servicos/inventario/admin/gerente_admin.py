from unfold.admin import ModelAdmin
from unfold.admin import TabularInline

from plataforma_de_servicos.inventario.models import InventarioSaldo


class InventarioSaldoInline(TabularInline):
    model = InventarioSaldo
    extra = 0
    max_num = 0
    min_num = 0
    can_delete = False
    show_change_link = False


class InventarioGerenteAdmin(ModelAdmin):
    list_display = ["nome", "slug", "is_ativo"]
    list_order_by = ["nome"]
    list_order_by_desc = ["-nome"]

    list_search = ["nome", "slug"]
    list_search_fields = ["nome", "slug"]

    search_fields = ["nome", "slug"]

    inlines = [InventarioSaldoInline]

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
