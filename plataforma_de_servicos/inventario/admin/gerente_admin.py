from unfold.admin import ModelAdmin
from unfold.admin import TabularInline

from plataforma_de_servicos.estoque.models.proxys.estoque_entrada import EstoqueEntrada
from plataforma_de_servicos.estoque.models.proxys.estoque_saida import EstoqueSaida
from plataforma_de_servicos.inventario.models import InventarioSaldo


class InventarioSaldoInline(TabularInline):
    model = InventarioSaldo
    extra = 0
    max_num = 0
    min_num = 0
    can_delete = False
    readonly_fields = ["produto", "quantidade"]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(quantidade__gt=0)


# TODO CORRIGIR PARA ESTOQUE ITENS E FILTRAR GET_QUERYSET PELO MOVIMENTO DE ENTRADA.
class InventarioEntradaInline(TabularInline):
    model = EstoqueEntrada

    fk_name = "inventario_destino"
    extra = 0
    max_num = 0

    readonly_fields = ["inventario_destino", "funcionario", "nf", "movimento", "processado"]
    can_delete = False
    show_change_link = True
    show_full_result_count = True
    exclude = ["inventario_origem"]

    title = "Entradas"

    def has_add_permission(self, request, obj):
        return False


# TODO CORRIGIR PARA ESTOQUE ITENS E FILTRAR GET_QUERYSET PELO MOVIMENTO DE SAÍDA.
class InventarioSaidaInline(TabularInline):
    model = EstoqueSaida

    fk_name = "inventario_origem"

    title = "Saídas"

    readonly_fields = ["inventario_destino", "inventario_origem", "funcionario", "nf", "movimento", "processado"]

    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj):
        return False


class InventarioGerenteAdmin(ModelAdmin):
    list_display = ["nome", "slug", "is_ativo"]
    list_order_by = ["nome"]
    list_order_by_desc = ["-nome"]

    list_search = ["nome", "slug"]
    list_search_fields = ["nome", "slug"]

    search_fields = ["nome", "slug"]

    inlines = [InventarioSaldoInline, InventarioEntradaInline, InventarioSaidaInline]

    compressed_fields = True
    warn_unsaved_form = True

    list_filter_submit = True
    list_fullwidth = True

    actions_list = []  # Displayed above the results list
    actions_row = []  # Displayed in a table row in results list
    actions_detail = []  # Displayed at the top of for in object detail
    actions_submit_line = []  # Displayed near save in object detail

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
