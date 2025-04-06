from typing import Any

from django import forms
from unfold.admin import ModelAdmin
from unfold.admin import TabularInline

from plataforma_de_servicos.estoque.models.estoque_itens_model import EstoqueItens
from plataforma_de_servicos.estoque.models.protocolo_entrega_itens_model import (
    ProtocoloEntregaItens,
)


class EstoqueItensInline(TabularInline):
    model = EstoqueItens
    extra = 0
    readonly_fields = ("saldo",)


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
        # Definir o valor padrão para o campo 'movimento' como 'entrada', por exemplo
        form.base_fields["movimento"].initial = "e"
        # Para ocultar o campo 'movimento' do formulário
        if "movimento" in form.base_fields:
            form.base_fields["movimento"].widget = forms.HiddenInput()
        return form

    def save_related(self, request: Any, form: Any, formsets: Any, change: Any) -> None:
        """
        ### Portuguese
        O método save_related é chamado após o salvamento
        do formulário principal e dos formulários inline.
        Ou seja, após salvar todos os itens de estoque
        relacionados a esta instancia de entrada de estoque.

        Desta forma, após salvar todos os itens de estoque,
        chamamos o método processar da instancia de entrada
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
        # Definir o valor padrão para o campo 'movimento' como 'entrada', por exemplo
        form.base_fields["movimento"].initial = "s"
        # Para ocultar o campo 'movimento' do formulário
        if "movimento" in form.base_fields:
            form.base_fields["movimento"].widget = forms.HiddenInput()
        return form

    def save_related(self, request: Any, form: Any, formsets: Any, change: Any) -> None:
        super().save_related(request, form, formsets, change)
        obj = form.instance
        obj.processar()


class ProtocoloEntregaItensInline(TabularInline):
    model = ProtocoloEntregaItens
    extra = 0


class ProtocoloEntregaAdmin(ModelAdmin):
    inlines = (ProtocoloEntregaItensInline,)
    list_display = ("__str__", "estoque_atualizado")
    list_filter = ("usuario",)
    date_hierarchy = "created"

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

    def save_related(self, request: Any, form: Any, formsets: Any, change: Any) -> None:
        super().save_related(request, form, formsets, change)
        obj = form.instance
        user = request.user
        obj.processar_protocolo(usuario=user)
