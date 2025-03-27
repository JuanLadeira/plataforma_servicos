from typing import Any

from django import forms
from django.contrib import admin

from plataforma_de_servicos.estoque.models.estoque_itens_model import EstoqueItens
from plataforma_de_servicos.estoque.models.protocolo_entrega_itens_model import (
    ProtocoloEntregaItens,
)
from plataforma_de_servicos.estoque.models.protocolo_entrega_model import (
    ProtocoloEntrega,
)
from plataforma_de_servicos.estoque.models.proxys.estoque_entrada import EstoqueEntrada
from plataforma_de_servicos.estoque.models.proxys.estoque_saida import EstoqueSaida


class EstoqueItensInline(admin.TabularInline):
    model = EstoqueItens
    extra = 0
    readonly_fields = ("saldo",)


@admin.register(EstoqueEntrada)
class EstoqueEntradaAdmin(admin.ModelAdmin):
    inlines = (EstoqueItensInline,)
    list_display = ("__str__", "nf", "funcionario")
    search_fields = ("nf",)
    list_filter = ("funcionario",)
    date_hierarchy = "created"
    verbose_name = "Entrada de estoque"
    verbose_name_plural = "Entradas de estoque"

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


@admin.register(EstoqueSaida)
class EstoqueSaidaAdmin(admin.ModelAdmin):
    inlines = (EstoqueItensInline,)
    list_display = ("__str__", "nf", "funcionario")
    search_fields = ("nf",)
    list_filter = ("funcionario",)
    date_hierarchy = "created"
    verbose_name = "Saída de estoque"

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


class ProtocoloEntregaItensInline(admin.TabularInline):
    model = ProtocoloEntregaItens
    extra = 0


@admin.register(ProtocoloEntrega)
class ProtocoloEntregaAdmin(admin.ModelAdmin):
    inlines = (ProtocoloEntregaItensInline,)
    list_display = ("__str__", "estoque_atualizado")
    list_filter = ("usuario",)
    date_hierarchy = "created"

    def save_related(self, request: Any, form: Any, formsets: Any, change: Any) -> None:
        super().save_related(request, form, formsets, change)
        obj = form.instance
        user = request.user
        obj.processar_protocolo(usuario=user)
