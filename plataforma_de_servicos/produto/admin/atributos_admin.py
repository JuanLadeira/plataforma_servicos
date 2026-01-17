from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from ..models import Atributo, ValorAtributo


@admin.register(Atributo)
class AtributoAdmin(ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)


class ValorAtributoInline(TabularInline):
    model = ValorAtributo
    extra = 1


@admin.register(ValorAtributo)
class ValorAtributoAdmin(ModelAdmin):
    list_display = ("atributo", "valor")
    list_filter = ("atributo",)
    search_fields = ("valor", "atributo__nome")