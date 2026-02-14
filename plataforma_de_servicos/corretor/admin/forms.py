from django import forms
from django.utils.translation import gettext_lazy as _

from unfold.widgets import UnfoldAdminTextareaWidget


class DescarteInteresseForm(forms.Form):
    """Formulário para coletar motivo do descarte do interesse."""

    motivo = forms.CharField(
        label=_("Motivo do descarte"),
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 4}),
        required=False,
        help_text=_("Informe o motivo pelo qual o interesse está sendo descartado (opcional)."),
    )
