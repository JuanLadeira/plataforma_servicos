from typing import Any

from django import forms
from django.contrib import admin

from plataforma_de_servicos.estoque.choices.movimento import Movimento
from plataforma_de_servicos.estoque.models.estoque_itens_model import EstoqueItens
from plataforma_de_servicos.estoque.models.proxys.estoque_entrada import EstoqueEntrada
from plataforma_de_servicos.estoque.models.proxys.estoque_saida import EstoqueSaida
from plataforma_de_servicos.users.models import User


class EstoqueItensInline(admin.TabularInline):
    model = EstoqueItens
    extra = 0
    readonly_fields = ("saldo",)


class FuncionarioFilter(admin.SimpleListFilter):
    title = "funcionario"
    parameter_name = "funcionario"

    def lookups(self, request, model_admin):
        if not request.user.is_superuser:
            # Filter lookups to current user's company
            funcionarios = User.objects.filter(funcionario__empresa=request.user.funcionario.empresa)
            return [(f.id, f.email) for f in funcionarios]
        # Superuser sees all
        return [(f.id, f.email) for f in User.objects.all()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(funcionario__id=self.value())
        return queryset


@admin.register(EstoqueEntrada)
class EstoqueEntradaAdmin(admin.ModelAdmin):
    inlines = (EstoqueItensInline,)
    list_display = ("__str__", "nf", "funcionario")
    search_fields = ("nf",)
    list_filter = (FuncionarioFilter,)
    date_hierarchy = "created"
    verbose_name = "Entrada de estoque"
    verbose_name_plural = "Entradas de estoque"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(empresa=request.user.funcionario.empresa)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "funcionario":
            if not request.user.is_superuser:
                kwargs["queryset"] = User.objects.filter(
                    funcionario__empresa=request.user.funcionario.empresa,
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Definir o valor padrão para o campo 'movimento' como 'entrada', por exemplo
        form.base_fields["movimento"].initial = Movimento.ENTRADA.value

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
        entrada = form.instance
        super().save_related(request, form, formsets, change)
        entrada.processar()


@admin.register(EstoqueSaida)
class EstoqueSaidaAdmin(admin.ModelAdmin):
    inlines = (EstoqueItensInline,)
    list_display = ("__str__", "nf", "funcionario")
    search_fields = ("nf",)
    list_filter = (FuncionarioFilter,)
    date_hierarchy = "created"
    verbose_name = "Saída de estoque"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(empresa=request.user.funcionario.empresa)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "funcionario":
            if not request.user.is_superuser:
                kwargs["queryset"] = User.objects.filter(
                    funcionario__empresa=request.user.funcionario.empresa,
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Definir o valor padrão para o campo 'movimento' como 'entrada', por exemplo
        form.base_fields["movimento"].initial = Movimento.SAIDA.value
        # Para ocultar o campo 'movimento' do formulário
        if "movimento" in form.base_fields:
            form.base_fields["movimento"].widget = forms.HiddenInput()
        return form

    def save_related(self, request: Any, form: Any, formsets: Any, change: Any) -> None:
        super().save_related(request, form, formsets, change)
        obj = form.instance
        obj.processar()
