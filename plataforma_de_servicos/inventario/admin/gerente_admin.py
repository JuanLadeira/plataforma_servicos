from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.admin import TabularInline

from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.estoque.models.estoque_itens_model import EstoqueItens
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


class EstoqueItensEntradaInline(TabularInline):
    """Inline para exibir itens de ENTRADA de estoque no inventário."""
    model = EstoqueItens
    fk_name = "inventario"
    extra = 0
    max_num = 0
    min_num = 0
    can_delete = False
    verbose_name = "Item de Entrada"
    verbose_name_plural = "Itens de Entrada"

    readonly_fields = [
        "produto",
        "quantidade",
        "saldo",
        "data_movimento",
        "nf_movimento",
        "funcionario_movimento",
    ]
    fields = readonly_fields

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(
            estoque__movimento=Movimento.ENTRADA.value
        ).select_related("estoque", "estoque__funcionario", "produto")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Data")
    def data_movimento(self, obj):
        return obj.estoque.created.strftime("%d/%m/%Y %H:%M") if obj.estoque else "-"

    @admin.display(description="NF")
    def nf_movimento(self, obj):
        return obj.estoque.nf if obj.estoque else "-"

    @admin.display(description="Funcionário")
    def funcionario_movimento(self, obj):
        return obj.estoque.funcionario if obj.estoque else "-"


class EstoqueItensSaidaInline(TabularInline):
    """Inline para exibir itens de SAÍDA de estoque no inventário."""
    model = EstoqueItens
    fk_name = "inventario"
    extra = 0
    max_num = 0
    min_num = 0
    can_delete = False
    verbose_name = "Item de Saída"
    verbose_name_plural = "Itens de Saída"

    readonly_fields = [
        "produto",
        "quantidade",
        "saldo",
        "data_movimento",
        "nf_movimento",
        "funcionario_movimento",
        "origem_saida_display",
    ]
    fields = readonly_fields

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(
            estoque__movimento=Movimento.SAIDA.value
        ).select_related("estoque", "estoque__funcionario", "produto")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Data")
    def data_movimento(self, obj):
        return obj.estoque.created.strftime("%d/%m/%Y %H:%M") if obj.estoque else "-"

    @admin.display(description="NF")
    def nf_movimento(self, obj):
        return obj.estoque.nf if obj.estoque else "-"

    @admin.display(description="Funcionário")
    def funcionario_movimento(self, obj):
        return obj.estoque.funcionario if obj.estoque else "-"

    @admin.display(description="Origem")
    def origem_saida_display(self, obj):
        return obj.estoque.get_origem_saida_display() if obj.estoque and obj.estoque.origem_saida else "-"


class InventarioGerenteAdmin(ModelAdmin):
    list_display = ["nome", "slug", "is_ativo", "exibir_na_vitrine"]
    list_filter = ["is_ativo", "exibir_na_vitrine"]
    list_editable = ["exibir_na_vitrine"]
    list_order_by = ["nome"]
    list_order_by_desc = ["-nome"]

    list_search = ["nome", "slug"]
    list_search_fields = ["nome", "slug"]

    search_fields = ["nome", "slug"]

    fieldsets = [
        (
            "Informações Básicas",
            {
                "fields": ["nome", "slug", "is_ativo"],
            },
        ),
        (
            "Configurações de Exibição",
            {
                "fields": ["exibir_na_vitrine"],
                "description": "Configure se os produtos deste inventário devem aparecer na vitrine da página inicial.",
            },
        ),
    ]
    readonly_fields = ["slug"]

    inlines = [InventarioSaldoInline, EstoqueItensEntradaInline, EstoqueItensSaidaInline]

    compressed_fields = True
    warn_unsaved_form = True

    list_filter_submit = True
    list_fullwidth = True

    actions_list = []
    actions_row = []
    actions_detail = []
    actions_submit_line = []

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
