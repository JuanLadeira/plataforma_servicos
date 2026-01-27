from typing import Any

from django import forms
from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.admin import TabularInline

from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.estoque.models.estoque_itens_model import EstoqueItens
from plataforma_de_servicos.produto.models import VariacaoProduto


class EstoqueItensInline(TabularInline):
    model = EstoqueItens
    extra = 0
    fields = ("produto", "variacao", "quantidade", "saldo", "inventario")
    readonly_fields = ("saldo", "inventario")
    autocomplete_fields = ("produto", "variacao")

    def get_readonly_fields(self, request, obj=None):
        """Se estoque já existe (edição), todos os campos são readonly."""
        if obj and obj.pk:
            return ("produto", "variacao", "quantidade", "saldo", "inventario")
        return ("saldo", "inventario")

    def has_add_permission(self, request, obj=None):
        """Não permite adicionar itens em estoque já criado."""
        if obj and obj.pk:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        """Não permite deletar itens em estoque já criado."""
        if obj and obj.pk:
            return False
        return True

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "variacao":
            kwargs["queryset"] = VariacaoProduto.objects.select_related(
                "produto"
            ).prefetch_related("valores", "valores__atributo")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


def get_inventario(estoque):
    if estoque.movimento == Movimento.ENTRADA.value:
        return estoque.inventario_destino
    if estoque.movimento == Movimento.SAIDA.value:
        return estoque.inventario_origem
    if estoque.movimento == Movimento.TRANSFERENCIA.value:
        return estoque.inventario_destino
    return None


class EstoqueEntradaAdmin(ModelAdmin):
    inlines = (EstoqueItensInline,)
    list_display = ("__str__", "nf", "funcionario", "data")
    search_fields = ("nf", "data")
    list_filter = ("funcionario",)

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

    def get_readonly_fields(self, request, obj=None):
        """
        Se estoque já existe (edição), todos os campos são readonly,
        exceto 'nf' se estiver vazio.
        """
        if obj and obj.pk:
            readonly = ["inventario_destino", "funcionario", "observacao"]
            if obj.nf:
                readonly.append("nf")
            return readonly
        return ()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        if "movimento" in form.base_fields:
            form.base_fields["movimento"].initial = Movimento.ENTRADA.value
            form.base_fields["movimento"].widget = forms.HiddenInput()
        if "processado" in form.base_fields:
            form.base_fields["processado"].widget = forms.HiddenInput()
        if "inventario_origem" in form.base_fields:
            form.base_fields["inventario_origem"].widget = forms.HiddenInput()
        return form

    def has_delete_permission(self, request, obj=None):
        """Não permite deletar entradas de estoque já processadas."""
        if obj and obj.pk:
            return False
        return True

    def save_related(self, request: Any, form: Any, formsets: Any, change: Any) -> None:
        """
        O método save_related é chamado após o salvamento
        do formulário principal e dos formulários inline.
        Só processa na criação (change=False), não na edição.
        """
        super().save_related(request, form, formsets, change)
        if not change:
            obj = form.instance
            obj.processar()

    def save_formset(self, request, form, formset, change):
        # Só processa na criação
        if not change:
            instances = formset.save(commit=False)
            entrada = form.instance

            inventario = get_inventario(entrada)

            for instance in instances:
                instance.inventario = inventario
                instance.save()
            formset.save_m2m()


class EstoqueSaidaAdmin(ModelAdmin):
    inlines = (EstoqueItensInline,)
    list_display = ("__str__", "nf", "funcionario", "origem_saida", "pedido_id")
    search_fields = ("nf",)
    list_filter = ("funcionario", "origem_saida")

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

    fieldsets = [
        (
            "Informações da Saída",
            {
                "fields": [
                    "inventario_origem",
                    "funcionario",
                    "nf",
                ],
                "description": "Dados básicos da saída de estoque."
            },
        ),
        (
            "Detalhes da Saída",
            {
                "fields": [
                    "origem_saida",
                    "observacao",
                ],
                "description": "Motivo da saída (opcional). Se for uma saída automática de pedido, o campo 'ID do Pedido' será preenchido automaticamente."
            },
        ),
        (
            "Informações do Sistema",
            {
                "fields": [
                    "pedido_id",
                ],
                "classes": ["collapse"],
                "description": "Campos preenchidos automaticamente pelo sistema."
            },
        ),
    ]

    def get_readonly_fields(self, request, obj=None):
        """
        Se estoque já existe (edição), todos os campos são readonly,
        exceto 'nf' se estiver vazio (para permitir adicionar NF em saídas automáticas).
        """
        if obj and obj.pk:
            # Campos sempre readonly em edição
            readonly = ["inventario_origem", "funcionario", "origem_saida", "observacao", "pedido_id"]
            # Se NF já tem valor, também é readonly
            if obj.nf:
                readonly.append("nf")
            return readonly
        return ("pedido_id",)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        if "movimento" in form.base_fields:
            form.base_fields["movimento"].initial = Movimento.SAIDA.value
            form.base_fields["movimento"].widget = forms.HiddenInput()

        if "processado" in form.base_fields:
            form.base_fields["processado"].widget = forms.HiddenInput()

        if "inventario_destino" in form.base_fields:
            form.base_fields["inventario_destino"].widget = forms.HiddenInput()

        # Tornar origem_saida não obrigatório
        if "origem_saida" in form.base_fields:
            form.base_fields["origem_saida"].required = False

        return form

    def has_delete_permission(self, request, obj=None):
        """Não permite deletar saídas de estoque já processadas."""
        if obj and obj.pk:
            return False
        return True

    def save_related(self, request: Any, form: Any, formsets: Any, change: Any) -> None:
        super().save_related(request, form, formsets, change)
        # Só processa na criação (change=False), não na edição
        if not change:
            obj = form.instance
            obj.processar()

    def save_formset(self, request, form, formset, change):
        # Só processa na criação
        if not change:
            instances = formset.save(commit=False)
            saida = form.instance

            inventario = get_inventario(saida)

            for instance in instances:
                instance.inventario = inventario
                instance.save()
            formset.save_m2m()
