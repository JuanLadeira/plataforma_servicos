from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from ..models import Atributo, ValorAtributo


class ValorAtributoInline(TabularInline):
    model = ValorAtributo
    extra = 1
    fields = ['valor', 'preco_adicional', 'percentual_adicional']


class AtributoAdmin(ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)
    inlines = [ValorAtributoInline]


class ValorAtributoAdmin(ModelAdmin):
    list_display = ("atributo", "valor", "preco_adicional", "percentual_adicional")
    list_filter = ("atributo",)
    search_fields = ("valor", "atributo__nome")
    list_editable = ("preco_adicional", "percentual_adicional")
    fieldsets = [
        ("Atributo", {
            "fields": ["atributo", "valor"]
        }),
        ("Modificadores de Preço", {
            "fields": ["preco_adicional", "percentual_adicional"],
            "description": "Configure modificações no preço base quando este atributo for selecionado"
        })
    ]