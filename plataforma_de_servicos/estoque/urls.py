"""
URLs para o módulo de estoque.
"""
from django.urls import path

from .views.saldo_view import get_saldo_variacao
from .views.variacao_autocomplete import variacao_autocomplete

app_name = "estoque"

urlpatterns = [
    path("api/saldo-variacao/", get_saldo_variacao, name="saldo-variacao"),
    path("api/variacao-autocomplete/", variacao_autocomplete, name="variacao-autocomplete"),
]
