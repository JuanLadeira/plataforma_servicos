from django.contrib import admin
from django import forms
from unfold.admin import ModelAdmin, TabularInline

from ..models import Atributo, ValorAtributo


class ValorAtributoForm(forms.ModelForm):
    """Formulário com validação de exclusividade para modificadores de preço."""

    class Meta:
        model = ValorAtributo
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        preco = cleaned_data.get('preco_adicional') or 0
        percentual = cleaned_data.get('percentual_adicional') or 0

        if preco > 0 and percentual > 0:
            raise forms.ValidationError(
                "Escolha apenas uma opção: preço adicional OU percentual adicional, não ambos."
            )
        return cleaned_data


class ValorAtributoInline(TabularInline):
    model = ValorAtributo
    form = ValorAtributoForm
    extra = 1
    fields = ['valor', 'preco_adicional', 'percentual_adicional']


class AtributoAdmin(ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)
    inlines = [ValorAtributoInline]


class ValorAtributoAdmin(ModelAdmin):
    form = ValorAtributoForm
    list_display = ("atributo", "valor", "preco_adicional", "percentual_adicional")
    list_filter = ("atributo",)
    search_fields = ("valor", "atributo__nome")
    list_editable = ("preco_adicional", "percentual_adicional")
    fieldsets = [
        ("Atributo", {
            "fields": ["atributo", "valor"]
        }),
        ("Modificadores de Preço (escolha apenas um)", {
            "fields": ["preco_adicional", "percentual_adicional"],
            "description": "Use preço adicional para valor fixo (ex: +R$ 5,00) OU percentual adicional para acréscimo proporcional (ex: +10%). Não é permitido usar ambos."
        })
    ]