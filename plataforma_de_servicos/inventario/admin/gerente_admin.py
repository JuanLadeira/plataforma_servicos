from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.admin import TabularInline

from plataforma_de_servicos.core.admin.mixins import TenantAwareAdminMixin
from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.estoque.models.estoque_itens_model import EstoqueItens
from plataforma_de_servicos.inventario.models import InventarioSaldo


class InventarioSaldoInline(TabularInline):
    """Inline para saldo por variação."""
    model = InventarioSaldo
    extra = 0
    max_num = 0
    min_num = 0
    can_delete = False
    readonly_fields = ["variacao_display", "quantidade"]
    fields = readonly_fields
    verbose_name = "Saldo por Variação"
    verbose_name_plural = "Saldos por Variação"

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(quantidade__gt=0).select_related(
            "produto", "variacao"
        ).prefetch_related("variacao__valores").order_by("produto__produto", "variacao__sku")

    @admin.display(description="Variação")
    def variacao_display(self, obj):
        if obj.variacao:
            valores = ", ".join(v.valor for v in obj.variacao.valores.all())
            return f"{obj.produto.produto} - {valores}" if valores else obj.produto.produto
        return obj.produto.produto


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
        "variacao_display",
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
        ).select_related(
            "estoque", "estoque__funcionario", "produto", "variacao"
        ).prefetch_related("variacao__valores").order_by("-estoque__created")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Variação")
    def variacao_display(self, obj):
        if obj.variacao:
            valores = ", ".join(v.valor for v in obj.variacao.valores.all())
            return f"{obj.produto.produto} - {valores}" if valores else obj.produto.produto
        return obj.produto.produto

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
        "variacao_display",
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
        ).select_related(
            "estoque", "estoque__funcionario", "produto", "variacao"
        ).prefetch_related("variacao__valores").order_by("-estoque__created")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Variação")
    def variacao_display(self, obj):
        if obj.variacao:
            valores = ", ".join(v.valor for v in obj.variacao.valores.all())
            return f"{obj.produto.produto} - {valores}" if valores else obj.produto.produto
        return obj.produto.produto

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


class InventarioGerenteAdmin(TenantAwareAdminMixin, ModelAdmin):
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
