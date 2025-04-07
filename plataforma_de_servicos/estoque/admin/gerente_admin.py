from typing import Any

from django import forms
from unfold.admin import ModelAdmin
from unfold.admin import TabularInline

from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.estoque.models.estoque_itens_model import EstoqueItens


class EstoqueItensInline(TabularInline):
    model = EstoqueItens
    extra = 0
    readonly_fields = ("saldo", "inventario")


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

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        form.base_fields["movimento"].initial = Movimento.ENTRADA.value

        if "movimento" in form.base_fields:
            form.base_fields["movimento"].widget = forms.HiddenInput()
        if "processado" in form.base_fields:
            form.base_fields["processado"].widget = forms.HiddenInput()
        if "inventario_origem" in form.base_fields:
            form.base_fields["inventario_origem"].widget = forms.HiddenInput()
        return form

    def save_related(self, request: Any, form: Any, formsets: Any, change: Any) -> None:
        """
        ### Portuguese
        O método save_related é chamado após o salvamento
        do formulário principal e dos formulários inline.
        Ou seja, após salvar todos os itens de estoque
        relacionados a esta instancia de estoque de estoque.

        Desta forma, após salvar todos os itens de estoque,
        chamamos o método processar da instancia de estoque
        de estoque para atualizar
        o saldo dos produtos relacionados a cada item.

        ### English
        The save_related method is called after
        saving the main form and inline forms.
        That is, after saving all stock items related
        to this stock entry instance.

        In this way, after saving all stock items,
        we call the process method of the stock entry
        instance to update the balance of the products
        related to each item.
        """
        super().save_related(request, form, formsets, change)
        obj = form.instance
        obj.processar()

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        entrada = form.instance

        inventario = get_inventario(entrada)

        for instance in instances:
            instance.inventario = inventario
            instance.save()
        formset.save_m2m()


class EstoqueSaidaAdmin(ModelAdmin):
    inlines = (EstoqueItensInline,)
    list_display = ("__str__", "nf", "funcionario")
    search_fields = ("nf",)
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

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        form.base_fields["movimento"].initial = Movimento.SAIDA.value

        if "movimento" in form.base_fields:
            form.base_fields["movimento"].widget = forms.HiddenInput()
        return form

    def save_related(self, request: Any, form: Any, formsets: Any, change: Any) -> None:
        super().save_related(request, form, formsets, change)
        obj = form.instance
        obj.processar()

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        saida = form.instance

        inventario = get_inventario(saida)

        for instance in instances:
            instance.inventario = inventario
            instance.save()
        formset.save_m2m()
