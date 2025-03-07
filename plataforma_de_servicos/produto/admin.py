import csv

from django import forms
from django.contrib import admin
from django.http import HttpRequest
from django.http import HttpResponse
from django.utils import timezone

from plataforma_de_servicos.estoque.models.estoque_itens_model import EstoqueItens
from plataforma_de_servicos.produto.models.categoria_model import Categoria
from plataforma_de_servicos.produto.models.produto_model import Produto

MDATA = timezone.now().strftime("%Y-%m-%d")


class EstoqueItensInline(admin.TabularInline):
    verbose_name = "Movimentação"
    verbose_name_plural = "Ultimas movimentações"
    model = EstoqueItens
    readonly_fields = (
        "estoque",
        "movimento",
        "quantidade",
        "produto",
        "data",
        "saldo",
        "nf",
    )
    can_delete = False
    extra = 0

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj) -> bool:
        return False

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Definir o valor padrão para o campo 'movimento' como 'entrada', por exemplo
        # Para ocultar o campo 'movimento' do formulário
        if "estoque" in form.base_fields:
            form.base_fields["estoque"].widget = forms.HiddenInput()
        return form


class ProdudoInline(admin.TabularInline):
    model = Produto
    extra = 0
    min_num = 1

    def can_delete(self, request, obj=None):
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        return False


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "importado",
        "ncm",
        "preco",
        "estoque",
        "estoque_minimo",
        "categoria",
    )
    search_fields = ("produto",)
    list_filter = ("importado", "categoria")
    actions = ("export_as_csv", "export_as_xlsx")
    readonly_fields = ("estoque",)

    inlines = [EstoqueItensInline]

    class Media:
        js = (
            "https://code.jquery.com/jquery-3.3.1.min.js",
            "/static/js/estoque_admin.js",
        )

    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename={meta}.csv"
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])

        return response

    export_as_csv.short_description = "Exportar CSV"


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("__str__",)
    search_fields = ("categoria",)
    readonly_fields = ("slug",)

    inlines = [ProdudoInline]
